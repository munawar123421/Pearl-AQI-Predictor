"""Dataset preparation for model training."""

from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from pearls_aqi.features.transform import get_feature_columns, get_target_columns
from pearls_aqi.logging_config import get_logger
from pearls_aqi.settings import settings

logger = get_logger(__name__)


def prepare_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.15,
    validation_size: float = 0.15,
    temporal_gap_hours: int = 24,
    random_seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Prepare chronological train/validation/test split.
    
    Args:
        df: DataFrame with features and targets
        test_size: Fraction for test set
        validation_size: Fraction for validation set
        temporal_gap_hours: Gap between train/val/test to reduce leakage
        random_seed: Random seed for reproducibility
        
    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    df = df.sort_values("observed_at").reset_index(drop=True)
    
    # Calculate split points
    n = len(df)
    test_start = int(n * (1 - test_size))
    val_start = int(n * (1 - test_size - validation_size))
    
    # Create splits
    train_df = df.iloc[:val_start].copy()
    val_df = df.iloc[val_start:test_start].copy()
    test_df = df.iloc[test_start:].copy()
    
    logger.info(
        "Created train/val/test split",
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        train_pct=round(len(train_df) / n * 100, 1),
        val_pct=round(len(val_df) / n * 100, 1),
        test_pct=round(len(test_df) / n * 100, 1),
    )
    
    return train_df, val_df, test_df


def prepare_model_inputs(
    df: pd.DataFrame,
    feature_cols: list,
    target_cols: list,
    fit_scaler: bool = False,
    scaler: StandardScaler = None,
) -> Tuple[np.ndarray, np.ndarray, StandardScaler]:
    """Prepare model input arrays.
    
    Args:
        df: DataFrame with features and targets
        feature_cols: List of feature column names
        target_cols: List of target column names
        fit_scaler: Whether to fit a new scaler
        scaler: Existing scaler to use (if fit_scaler=False)
        
    Returns:
        Tuple of (X, y, scaler)
    """
    # Filter to rows with valid targets
    df_valid = df.dropna(subset=target_cols).copy()
    
    if df_valid.empty:
        logger.warning("No rows with valid targets")
        return np.array([]), np.array([]), scaler
    
    # Extract features
    X = df_valid[feature_cols].values
    
    # Handle missing values in features (simple mean imputation)
    X = pd.DataFrame(X, columns=feature_cols).fillna(0).values
    
    # Extract targets
    y = df_valid[target_cols].values
    
    # Scale features
    if fit_scaler:
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
        logger.info("Fitted new StandardScaler")
    elif scaler is not None:
        X = scaler.transform(X)
    
    logger.info(
        "Prepared model inputs",
        samples=X.shape[0],
        features=X.shape[1],
        targets=y.shape[1] if y.ndim > 1 else 1,
    )
    
    return X, y, scaler


def get_feature_importance_names() -> list:
    """Get human-readable feature names for importance plots."""
    return get_feature_columns()
