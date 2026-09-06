"""Baseline models for AQI prediction."""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin

from pearls_aqi.logging_config import get_logger

logger = get_logger(__name__)


class NaivePredictor(BaseEstimator, RegressorMixin):
    """Naive baseline that predicts the last known AQI."""

    def __init__(self):
        """Initialize naive predictor."""
        self.last_known_aqi_ = None

    def fit(self, X, y):
        """Fit the model (just stores last AQI from training).
        
        Args:
            X: Feature matrix (not used, but required for sklearn interface)
            y: Target array [n_samples, n_targets]
        """
        # Use mean of first target column as baseline
        if y.ndim == 1:
            self.last_known_aqi_ = np.mean(y)
        else:
            self.last_known_aqi_ = np.mean(y[:, 0])
        
        logger.info("Fitted NaivePredictor", baseline_aqi=round(self.last_known_aqi_, 2))
        return self

    def predict(self, X):
        """Predict using the last known AQI.
        
        Args:
            X: Feature matrix [n_samples, n_features]
            
        Returns:
            Predictions array [n_samples, n_targets]
        """
        n_samples = X.shape[0]
        # Return same value for all forecast horizons
        predictions = np.full((n_samples, 3), self.last_known_aqi_)
        return predictions


class PersistenceModel(BaseEstimator, RegressorMixin):
    """Persistence model that uses current AQI as forecast."""

    def __init__(self, aqi_feature_idx: int = 10):
        """Initialize persistence model.
        
        Args:
            aqi_feature_idx: Index of 'aqi_current' in feature array
        """
        self.aqi_feature_idx = aqi_feature_idx

    def fit(self, X, y):
        """Fit the model (no parameters to learn).
        
        Args:
            X: Feature matrix
            y: Target array (not used)
        """
        logger.info("Fitted PersistenceModel")
        return self

    def predict(self, X):
        """Predict using current AQI value.
        
        Args:
            X: Feature matrix [n_samples, n_features]
            
        Returns:
            Predictions array [n_samples, n_targets]
        """
        n_samples = X.shape[0]
        
        # Try to extract current AQI from features
        if X.shape[1] > self.aqi_feature_idx:
            current_aqi = X[:, self.aqi_feature_idx]
        else:
            # Fallback: use mean of all samples
            current_aqi = np.full(n_samples, 100.0)
        
        # Repeat current AQI for all horizons
        predictions = np.column_stack([current_aqi, current_aqi, current_aqi])
        
        return predictions


class SeasonalNaive(BaseEstimator, RegressorMixin):
    """Seasonal naive model using day-of-week patterns."""

    def __init__(self):
        """Initialize seasonal naive model."""
        self.seasonal_means_ = None

    def fit(self, X, y):
        """Fit the model by computing day-of-week means.
        
        Args:
            X: Feature matrix [n_samples, n_features] 
                 Expects day_of_week at index 1
            y: Target array
        """
        # Extract day of week (assuming it's the 2nd feature)
        day_of_week = X[:, 1].astype(int) if X.shape[1] > 1 else np.zeros(len(X), dtype=int)
        
        # Compute mean AQI for each day of week
        self.seasonal_means_ = {}
        for day in range(7):
            mask = day_of_week == day
            if mask.any():
                if y.ndim == 1:
                    self.seasonal_means_[day] = np.mean(y[mask])
                else:
                    self.seasonal_means_[day] = np.mean(y[mask, 0])
        
        # Use overall mean as fallback
        self.overall_mean_ = np.mean(y[:, 0] if y.ndim > 1 else y)
        
        logger.info("Fitted SeasonalNaive", patterns=len(self.seasonal_means_))
        return self

    def predict(self, X):
        """Predict using seasonal patterns.
        
        Args:
            X: Feature matrix [n_samples, n_features]
            
        Returns:
            Predictions array [n_samples, n_targets]
        """
        n_samples = X.shape[0]
        predictions = np.zeros((n_samples, 3))
        
        # Extract day of week
        day_of_week = X[:, 1].astype(int) if X.shape[1] > 1 else np.zeros(n_samples, dtype=int)
        
        for i in range(n_samples):
            # Get forecast for 1, 2, 3 days ahead
            for horizon in range(3):
                future_day = (day_of_week[i] + horizon + 1) % 7
                predictions[i, horizon] = self.seasonal_means_.get(
                    future_day, self.overall_mean_
                )
        
        return predictions
