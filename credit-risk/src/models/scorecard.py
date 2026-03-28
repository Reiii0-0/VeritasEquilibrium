import logging
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

from src.features.woe_iv import WoEBinner

logger = logging.getLogger(__name__)


class CreditScorecardModel(BaseEstimator, ClassifierMixin):
    """Credit Scorecard Pipeline leveraging WoEBinner and XGBoost."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.binner = WoEBinner()
        self.model = XGBClassifier(random_state=self.random_state, use_label_encoder=False, eval_metric="logloss")
        self.is_fitted = False

    def tune(self, X: pd.DataFrame, y: pd.Series, n_trials: int = 100) -> None:
        """Optimizes XGBoost hyperparameters using Optuna."""
        logger.info(f"Starting Optuna tuning for {n_trials} trials...")
        
        X_woe = self.binner.fit_transform(X, y)
        selected_features = self.binner.select_features(threshold=0.02)
        X_woe = X_woe[selected_features]

        def objective(trial: optuna.Trial) -> float:
            param = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 8),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
                "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 10.0),
            }

            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
            auc_scores = []
            
            for train_idx, val_idx in cv.split(X_woe, y):
                X_tr, X_val = X_woe.iloc[train_idx], X_woe.iloc[val_idx]
                y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                model = XGBClassifier(**param, random_state=self.random_state, use_label_encoder=False, eval_metric="logloss")
                model.fit(X_tr, y_tr)
                preds = model.predict_proba(X_val)[:, 1]
                auc_scores.append(roc_auc_score(y_val, preds))
                
            return float(np.mean(auc_scores))

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"Best trial AUC: {study.best_value}")
        self.model.set_params(**study.best_params)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "CreditScorecardModel":
        """Fits the WoE binner and the XGBoost classifier."""
        logger.info("Fitting CreditScorecardModel pipeline...")
        X_woe = self.binner.fit_transform(X, y)
        self.selected_features_ = self.binner.select_features(threshold=0.02)
        
        if not self.selected_features_:
            logger.warning("No features met the IV threshold. Using all features.")
            self.selected_features_ = list(X.columns)
            
        self.model.fit(X_woe[self.selected_features_], y)
        self.is_fitted = True
        logger.info("CreditScorecardModel fitting complete.")
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts probability of default (Charged Off)."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet.")
        X_woe = self.binner.transform(X)
        return self.model.predict_proba(X_woe[self.selected_features_])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts class labels (0=Fully Paid, 1=Charged Off)."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet.")
        X_woe = self.binner.transform(X)
        return self.model.predict(X_woe[self.selected_features_])

    def predict_score(self, X: pd.DataFrame) -> np.ndarray:
        """
        Calculates credit scores based on the Basel point scaling formula.
        Score = 600 + (20/ln(2)) * ln(odds)
        Where odds = P(Good) / P(Bad) = P(0) / P(1)
        """
        probas = self.predict_proba(X)[:, 1]
        eps = 1e-6
        # odds of being 'Good' (Fully Paid = 0) vs 'Bad' (Charged Off = 1)
        odds = (1.0 - probas + eps) / (probas + eps)
        
        # Scaling parameters
        factor = 20 / np.log(2)
        offset = 600
        
        scores = offset + factor * np.log(odds)
        # Cap scores to standard bounds 300 - 850
        return np.clip(np.round(scores), 300, 850).astype(int)

    def predict_risk_band(self, X: pd.DataFrame) -> List[str]:
        """Classifies predicted scores into discrete risk bands."""
        scores = self.predict_score(X)
        bands = []
        for s in scores:
            if s >= 750:
                bands.append("VERY_LOW")
            elif s >= 700:
                bands.append("LOW")
            elif s >= 650:
                bands.append("MEDIUM")
            elif s >= 600:
                bands.append("HIGH")
            else:
                bands.append("VERY_HIGH")
        return bands

    def save(self, path: str) -> None:
        """Saves the fitted pipeline to a file."""
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted model.")
        joblib.dump(self, path)
        logger.info(f"Model successfully saved to {path}")

    @classmethod
    def load(cls, path: str) -> "CreditScorecardModel":
        """Loads a fitted pipeline from a file."""
        model = joblib.load(path)
        logger.info(f"Model successfully loaded from {path}")
        return model
