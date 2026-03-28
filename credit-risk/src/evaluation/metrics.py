import logging
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
    roc_curve,
)

logger = logging.getLogger(__name__)


def evaluate_scorecard(y_true: np.ndarray, y_pred_proba: np.ndarray) -> Dict[str, Any]:
    """Computes comprehensive evaluation metrics for the scorecard model."""
    
    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    auc_roc = roc_auc_score(y_true, y_pred_proba)
    gini = 2 * auc_roc - 1
    
    # KS Statistic
    ks_stats = tpr - fpr
    ks_statistic = np.max(ks_stats)
    ks_idx = np.argmax(ks_stats)
    ks_threshold = thresholds[ks_idx]
    
    # Loss Metrics
    brier_score = brier_score_loss(y_true, y_pred_proba)
    lloss = log_loss(y_true, y_pred_proba)
    
    # Optimal Threshold (Youden's J)
    youden_j = tpr - fpr
    optimal_idx = np.argmax(youden_j)
    optimal_threshold = thresholds[optimal_idx]
    
    # Confusion Matrix at optimal threshold
    y_pred = (y_pred_proba >= optimal_threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Lorenz / CAP Data
    # Sort by descending probability of default
    sort_idx = np.argsort(y_pred_proba)[::-1]
    y_true_sorted = y_true[sort_idx]
    
    cum_pop = np.arange(1, len(y_true) + 1) / len(y_true)
    cum_bads = np.cumsum(y_true_sorted) / np.sum(y_true)
    
    # Accuracy Ratio (CAP Gini)
    accuracy_ratio = gini # mathematically equivalent in binary classification
    
    metrics = {
        "auc_roc": float(auc_roc),
        "gini": float(gini),
        "ks_statistic": float(ks_statistic),
        "ks_threshold": float(ks_threshold),
        "brier_score": float(brier_score),
        "log_loss": float(lloss),
        "optimal_threshold": float(optimal_threshold),
        "confusion_matrix": {
            "TP": int(tp),
            "TN": int(tn),
            "FP": int(fp),
            "FN": int(fn),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1)
        },
        "lorenz_curve": {"x": cum_pop.tolist(), "y": cum_bads.tolist()},
        "cap_curve": {"x": cum_pop.tolist(), "y": cum_bads.tolist()},
        "accuracy_ratio": float(accuracy_ratio)
    }
    
    return metrics


def plot_roc_curve(y_true: np.ndarray, y_pred_proba: np.ndarray, ax: Optional[plt.Axes] = None) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    auc_val = roc_auc_score(y_true, y_pred_proba)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    ax.plot(fpr, tpr, label=f"ROC Curve (AUC = {auc_val:.3f})")
    ax.plot([0, 1], [0, 1], "k--")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Receiver Operating Characteristic")
    ax.legend(loc="lower right")


def plot_ks_chart(y_true: np.ndarray, y_pred_proba: np.ndarray, ax: Optional[plt.Axes] = None) -> None:
    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    ks_stats = tpr - fpr
    ks_max = np.max(ks_stats)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    ax.plot(thresholds, tpr, label="Cumulative True Positives (Bads)")
    ax.plot(thresholds, fpr, label="Cumulative False Positives (Goods)")
    ax.plot(thresholds, ks_stats, label=f"KS Stat ({ks_max:.3f})", linestyle=":")
    
    ax.set_xlim([0, 1])
    ax.set_xlabel("Probability Threshold")
    ax.set_ylabel("Cumulative Proportion")
    ax.set_title("Kolmogorov-Smirnov (KS) Chart")
    ax.legend(loc="best")


def plot_lorenz_curve(y_true: np.ndarray, y_pred_proba: np.ndarray, ax: Optional[plt.Axes] = None) -> None:
    sort_idx = np.argsort(y_pred_proba)[::-1]
    y_true_sorted = y_true[sort_idx]
    
    cum_pop = np.arange(1, len(y_true) + 1) / len(y_true)
    cum_bads = np.cumsum(y_true_sorted) / np.sum(y_true)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    ax.plot(cum_pop, cum_bads, label="Lorenz Curve")
    ax.plot([0, 1], [0, 1], "k--", label="Random Selection")
    ax.set_xlabel("% Cumulative Population")
    ax.set_ylabel("% Cumulative Bads")
    ax.set_title("Lorenz Curve")
    ax.legend(loc="best")


def plot_score_distribution(scores: np.ndarray, y_true: np.ndarray, ax: Optional[plt.Axes] = None) -> None:
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    goods = scores[y_true == 0]
    bads = scores[y_true == 1]
    
    ax.hist(goods, bins=30, alpha=0.5, label="Fully Paid (Goods)", density=True)
    ax.hist(bads, bins=30, alpha=0.5, label="Charged Off (Bads)", density=True)
    
    ax.set_xlabel("Credit Score")
    ax.set_ylabel("Density")
    ax.set_title("Score Distribution by Class")
    ax.legend(loc="best")


def plot_calibration_curve(y_true: np.ndarray, y_pred_proba: np.ndarray, n_bins: int = 10, ax: Optional[plt.Axes] = None) -> None:
    from sklearn.calibration import calibration_curve
    
    prob_true, prob_pred = calibration_curve(y_true, y_pred_proba, n_bins=n_bins)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    ax.plot(prob_pred, prob_true, marker='o', label="Model Calibration")
    ax.plot([0, 1], [0, 1], "k--", label="Perfectly Calibrated")
    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Fraction of Positives")
    ax.set_title("Calibration Curve (Reliability Diagram)")
    ax.legend(loc="best")
