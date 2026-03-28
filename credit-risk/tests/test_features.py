import numpy as np
import pandas as pd
import pytest

from src.features.woe_iv import WoEBinner
from src.models.scorecard import CreditScorecardModel

# --- Synthetic Data Generation ---
@pytest.fixture
def synthetic_data():
    """Generates a small synthetic dataset for testing."""
    np.random.seed(42)
    n_samples = 200
    
    # Generate features
    loan_amnt = np.random.uniform(1000, 35000, n_samples)
    int_rate = np.random.uniform(5.0, 25.0, n_samples)
    annual_inc = np.random.uniform(30000, 150000, n_samples)
    emp_length = np.random.randint(0, 11, n_samples)
    grade = np.random.choice(["A", "B", "C", "D", "E"], n_samples)
    home_ownership = np.random.choice(["MORTGAGE", "RENT", "OWN"], n_samples)
    
    # Make target somewhat dependent on int_rate and grade to ensure some IV > 0.02
    prob_default = (int_rate / 25.0) * 0.5
    prob_default += np.where(grade == "A", -0.1, np.where(grade == "E", 0.2, 0.0))
    prob_default = np.clip(prob_default, 0.05, 0.95)
    target = np.random.binomial(1, prob_default)
    
    X = pd.DataFrame({
        "loan_amnt": loan_amnt,
        "int_rate": int_rate,
        "annual_inc": annual_inc,
        "emp_length": emp_length,
        "grade": grade,
        "home_ownership": home_ownership,
    })
    y = pd.Series(target, name="target")
    
    return X, y

# --- Tests for WoEBinner ---

def test_woebinner_initialization():
    binner = WoEBinner(fine_bins=10)
    assert binner.fine_bins == 10
    assert binner.bins == {}
    assert binner.woe_maps == {}

def test_woebinner_fit(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    binner.fit(X, y)
    
    assert "int_rate" in binner.woe_maps
    assert "grade" in binner.woe_maps
    assert len(binner.iv_scores) == X.shape[1]

def test_woebinner_transform(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    binner.fit(X, y)
    X_transformed = binner.transform(X)
    
    assert X_transformed.shape == X.shape
    assert all(X_transformed.dtypes == float)

def test_woebinner_fit_transform(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    X_transformed = binner.fit_transform(X, y)
    
    assert "grade" in binner.woe_maps
    assert X_transformed["grade"].dtype == float

def test_woebinner_iv_summary(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    binner.fit(X, y)
    
    summary = binner.get_iv_summary()
    assert isinstance(summary, pd.DataFrame)
    assert "feature" in summary.columns
    assert "IV" in summary.columns
    assert "power" in summary.columns
    assert len(summary) == X.shape[1]

def test_woebinner_select_features(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    binner.fit(X, y)
    
    # With a high threshold, we should get fewer features
    selected_high = binner.select_features(threshold=0.5)
    selected_low = binner.select_features(threshold=0.0)
    
    assert isinstance(selected_low, list)
    assert len(selected_low) >= len(selected_high)

def test_woebinner_unseen_categories(synthetic_data):
    X, y = synthetic_data
    binner = WoEBinner()
    binner.fit(X, y)
    
    # Introduce unseen category
    X_new = X.copy()
    X_new.loc[0, "grade"] = "Z_UNSEEN"
    
    # Should not raise KeyError, should map to global_woe
    X_trans = binner.transform(X_new)
    assert not X_trans["grade"].isna().any()

# --- Tests for CreditScorecardModel ---

def test_scorecard_model_fit_predict(synthetic_data):
    X, y = synthetic_data
    model = CreditScorecardModel(random_state=42)
    model.fit(X, y)
    
    preds = model.predict(X)
    assert len(preds) == len(X)
    assert set(np.unique(preds)).issubset({0, 1})

def test_scorecard_model_predict_proba(synthetic_data):
    X, y = synthetic_data
    model = CreditScorecardModel(random_state=42)
    model.fit(X, y)
    
    probas = model.predict_proba(X)
    assert probas.shape == (len(X), 2)
    assert np.all((probas >= 0) & (probas <= 1))

def test_scorecard_model_predict_score(synthetic_data):
    X, y = synthetic_data
    model = CreditScorecardModel(random_state=42)
    model.fit(X, y)
    
    scores = model.predict_score(X)
    assert len(scores) == len(X)
    assert np.all((scores >= 300) & (scores <= 850))

def test_scorecard_model_predict_risk_band(synthetic_data):
    X, y = synthetic_data
    model = CreditScorecardModel(random_state=42)
    model.fit(X, y)
    
    bands = model.predict_risk_band(X)
    valid_bands = {"VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
    assert len(bands) == len(X)
    assert all(band in valid_bands for band in bands)
