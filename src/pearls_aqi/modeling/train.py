"""Model training pipeline."""

import time
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from pearls_aqi.features.transform import get_feature_columns, get_target_columns
from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.baselines import NaivePredictor, PersistenceModel
from pearls_aqi.modeling.dataset import prepare_model_inputs, prepare_train_test_split

logger = get_logger(__name__)


def train_models(
    train_df, val_df, test_df, feature_cols: List[str], target_cols: List[str]
) -> Dict[str, Dict]:
    """Train and evaluate multiple models.
    
    Args:
        train_df: Training data
        val_df: Validation data
        test_df: Test data
        feature_cols: Feature column names
        target_cols: Target column names
        
    Returns:
        Dictionary of model results
    """
    results = {}
    
    # Prepare datasets
    X_train, y_train, scaler = prepare_model_inputs(
        train_df, feature_cols, target_cols, fit_scaler=True
    )
    X_val, y_val, _ = prepare_model_inputs(val_df, feature_cols, target_cols, scaler=scaler)
    X_test, y_test, _ = prepare_model_inputs(test_df, feature_cols, target_cols, scaler=scaler)
    
    if len(X_train) == 0:
        logger.error("No valid training data")
        return results
    
    # Define models to train
    models = {
        "naive": NaivePredictor(),
        "persistence": PersistenceModel(),
        "ridge": Ridge(alpha=1.0, random_state=42),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,
        ),
    }
    
    # Train each model
    for model_name, model in models.items():
        logger.info(f"Training {model_name}...")
        
        try:
            start_time = time.time()
            
            # Train
            model.fit(X_train, y_train)
            
            # Predict
            y_train_pred = model.predict(X_train)
            y_val_pred = model.predict(X_val)
            y_test_pred = model.predict(X_test)
            
            training_time = time.time() - start_time
            
            # Evaluate
            train_metrics = calculate_metrics(y_train, y_train_pred, target_cols)
            val_metrics = calculate_metrics(y_val, y_val_pred, target_cols)
            test_metrics = calculate_metrics(y_test, y_test_pred, target_cols)
            
            results[model_name] = {
                "model": model,
                "scaler": scaler,
                "train_metrics": train_metrics,
                "val_metrics": val_metrics,
                "test_metrics": test_metrics,
                "training_time": training_time,
                "feature_cols": feature_cols,
                "target_cols": target_cols,
            }
            
            logger.info(
                f"Trained {model_name}",
                val_mae=round(val_metrics["mae"], 2),
                val_rmse=round(val_metrics["rmse"], 2),
                val_r2=round(val_metrics["r2"], 3),
                time_sec=round(training_time, 2),
            )
            
        except Exception as e:
            logger.error(f"Failed to train {model_name}", error=str(e))
    
    return results


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, target_cols: List[str]) -> Dict:
    """Calculate evaluation metrics.
    
    Args:
        y_true: True values [n_samples, n_targets]
        y_pred: Predicted values [n_samples, n_targets]
        target_cols: Target column names
        
    Returns:
        Dictionary of metrics
    """
    # Ensure 2D arrays
    if y_true.ndim == 1:
        y_true = y_true.reshape(-1, 1)
    if y_pred.ndim == 1:
        y_pred = y_pred.reshape(-1, 1)
    
    # Overall metrics
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Per-horizon metrics
    horizon_metrics = {}
    for i, target_col in enumerate(target_cols):
        if i < y_true.shape[1]:
            horizon_mae = mean_absolute_error(y_true[:, i], y_pred[:, i])
            horizon_rmse = np.sqrt(mean_squared_error(y_true[:, i], y_pred[:, i]))
            horizon_r2 = r2_score(y_true[:, i], y_pred[:, i])
            
            horizon_metrics[target_col] = {
                "mae": float(horizon_mae),
                "rmse": float(horizon_rmse),
                "r2": float(horizon_r2),
            }
    
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "horizon_metrics": horizon_metrics,
        "n_samples": len(y_true),
    }


def select_champion(results: Dict[str, Dict], metric: str = "mae") -> str:
    """Select the best model based on validation metric.
    
    Args:
        results: Dictionary of model results
        metric: Metric to use for selection ('mae', 'rmse', or 'r2')
        
    Returns:
        Name of champion model
    """
    if not results:
        logger.warning("No models to select from")
        return None
    
    best_model = None
    best_score = float("inf") if metric in ["mae", "rmse"] else float("-inf")
    
    for model_name, result in results.items():
        val_metrics = result.get("val_metrics", {})
        score = val_metrics.get(metric, float("inf" if metric in ["mae", "rmse"] else "-inf"))
        
        if metric in ["mae", "rmse"]:
            if score < best_score:
                best_score = score
                best_model = model_name
        else:  # r2
            if score > best_score:
                best_score = score
                best_model = model_name
    
    logger.info(
        f"Selected champion model: {best_model}",
        metric=metric,
        score=round(best_score, 3),
    )
    
    return best_model
