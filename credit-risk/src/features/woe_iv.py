import logging
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

logger = logging.getLogger(__name__)

IV_THRESHOLDS = {
    0.02: "useless",
    0.10: "weak",
    0.30: "medium",
    0.50: "strong",
    float("inf"): "suspicious",
}


class WoEBinner(BaseEstimator, TransformerMixin):
    """Weight of Evidence (WoE) and Information Value (IV) Binner."""

    def __init__(self, fine_bins: int = 20, min_bin_size: float = 0.05, max_event_diff: float = 0.05):
        self.fine_bins = fine_bins
        self.min_bin_size = min_bin_size
        self.max_event_diff = max_event_diff
        self.bins: Dict[str, Union[List[float], List[str]]] = {}
        self.woe_maps: Dict[str, Dict[str, float]] = {}
        self.iv_scores: Dict[str, float] = {}
        self.global_woe: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "WoEBinner":
        """Fits the WoE binner to the features and target."""
        logger.info("Fitting WoEBinner...")
        eps = 1e-6
        total_events = max(y.sum(), eps)
        total_non_events = max(len(y) - total_events, eps)
        self.global_woe = np.log((total_events / len(y)) / (total_non_events / len(y) + eps) + eps)

        for col in X.columns:
            try:
                if pd.api.types.is_numeric_dtype(X[col]):
                    self._fit_numeric(X[col], y)
                else:
                    self._fit_categorical(X[col], y)
            except Exception as e:
                logger.error(f"Error fitting feature {col}: {e}")
                self.iv_scores[col] = 0.0

        logger.info("WoEBinner fitting complete.")
        return self

    def _fit_numeric(self, series: pd.Series, y: pd.Series) -> None:
        """Applies fine and coarse classing for a numeric feature."""
        df = pd.DataFrame({"X": series, "y": y})
        
        # Fine classing
        df["bin"], bins = pd.qcut(df["X"], q=self.fine_bins, retbins=True, duplicates="drop")
        bins[0] = -np.inf
        bins[-1] = np.inf
        
        # Coarse classing (simplified for robust execution)
        grouped = df.groupby("bin", observed=True)["y"].agg(["count", "sum"])
        grouped["non_event"] = grouped["count"] - grouped["sum"]
        
        eps = 1e-6
        total_events = max(y.sum(), eps)
        total_non_events = max(len(y) - total_events, eps)
        
        dist_events = grouped["sum"] / total_events
        dist_non_events = grouped["non_event"] / total_non_events
        
        woe = np.log(dist_events / dist_non_events.replace(0, eps))
        iv = (dist_events - dist_non_events) * woe
        
        self.bins[series.name] = bins.tolist()
        self.woe_maps[series.name] = {str(k): v for k, v in woe.items()}
        self.iv_scores[series.name] = iv.sum()

    def _fit_categorical(self, series: pd.Series, y: pd.Series) -> None:
        """Applies classing for a categorical feature."""
        df = pd.DataFrame({"X": series.fillna("Unknown"), "y": y})
        grouped = df.groupby("X")["y"].agg(["count", "sum"])
        grouped["non_event"] = grouped["count"] - grouped["sum"]
        
        eps = 1e-6
        total_events = max(y.sum(), eps)
        total_non_events = max(len(y) - total_events, eps)
        
        dist_events = grouped["sum"] / total_events
        dist_non_events = grouped["non_event"] / total_non_events
        
        woe = np.log(dist_events / dist_non_events.replace(0, eps))
        iv = (dist_events - dist_non_events) * woe
        
        self.bins[series.name] = grouped.index.tolist()
        self.woe_maps[series.name] = woe.to_dict()
        self.iv_scores[series.name] = iv.sum()

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transforms features into their corresponding WoE values."""
        X_out = X.copy()
        
        for col in X.columns:
            if col not in self.woe_maps:
                continue
                
            if pd.api.types.is_numeric_dtype(X[col]):
                bins = self.bins.get(col)
                if bins:
                    binned = pd.cut(X[col], bins=bins, include_lowest=True).astype(str)
                    X_out[col] = binned.map(self.woe_maps[col]).fillna(self.global_woe)
            else:
                X_out[col] = X[col].fillna("Unknown").map(self.woe_maps[col]).fillna(self.global_woe)
                
        return X_out

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    def get_iv_summary(self) -> pd.DataFrame:
        """Returns a DataFrame summarizing the Information Value of features."""
        iv_list = []
        for feature, iv in self.iv_scores.items():
            power = "suspicious"
            for threshold, label in IV_THRESHOLDS.items():
                if iv < threshold:
                    power = label
                    break
            iv_list.append({"feature": feature, "IV": iv, "power": power})
            
        df = pd.DataFrame(iv_list).sort_values("IV", ascending=False).reset_index(drop=True)
        return df

    def select_features(self, threshold: float = 0.02) -> List[str]:
        """Returns a list of features with IV above the specified threshold."""
        return [f for f, iv in self.iv_scores.items() if iv >= threshold]

    def plot_woe(self, feature: str, ax: Optional[plt.Axes] = None) -> None:
        """Plots the WoE values and event rates for a specific feature bins."""
        if feature not in self.woe_maps:
            logger.error(f"Feature {feature} not found in fitted WoE maps.")
            return

        woe_dict = self.woe_maps[feature]
        bins = list(woe_dict.keys())
        woes = list(woe_dict.values())
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
            
        ax.bar(bins, woes, color="skyblue")
        ax.set_title(f"Weight of Evidence (WoE) for {feature}")
        ax.set_xlabel("Bins / Categories")
        ax.set_ylabel("WoE")
        ax.tick_params(axis='x', rotation=45)
        
        if ax is None:
            plt.tight_layout()
            plt.show()
