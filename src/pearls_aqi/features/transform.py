"""Feature transformation and engineering."""

import math
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from pearls_aqi.logging_config import get_logger
from pearls_aqi.schemas import FeatureVector, Observation

logger = get_logger(__name__)


def create_time_features(dt: datetime) -> dict:
    """Create time-based features from datetime.
    
    Args:
        dt: Datetime object
        
    Returns:
        Dictionary of time features
    """
    hour = dt.hour
    month = dt.month
    
    return {
        "hour": hour,
        "day_of_week": dt.weekday(),
        "day_of_month": dt.day,
        "month": month,
        "week_of_year": dt.isocalendar()[1],
        "is_weekend": dt.weekday() >= 5,
        # Cyclical encoding
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
        "month_sin": math.sin(2 * math.pi * month / 12),
        "month_cos": math.cos(2 * math.pi * month / 12),
    }


def create_weather_features(observation: Observation) -> dict:
    """Create weather-based features.
    
    Args:
        observation: Observation with weather data
        
    Returns:
        Dictionary of weather features
    """
    features = {
        "temperature_c": observation.temperature_c,
        "humidity_pct": observation.humidity_pct,
        "pressure_hpa": observation.pressure_hpa,
        "wind_speed_ms": observation.wind_speed_ms,
        "cloud_pct": observation.cloud_pct,
        "precipitation_mm": observation.precipitation_mm,
    }
    
    # Wind direction as sin/cos
    if observation.wind_direction_deg is not None:
        rad = math.radians(observation.wind_direction_deg)
        features["wind_direction_sin"] = math.sin(rad)
        features["wind_direction_cos"] = math.cos(rad)
    else:
        features["wind_direction_sin"] = None
        features["wind_direction_cos"] = None
    
    return features


def create_lag_features(df: pd.DataFrame, column: str, lags: List[int]) -> pd.DataFrame:
    """Create lag features for a column.
    
    Args:
        df: DataFrame with time series data
        column: Column name to create lags for
        lags: List of lag periods (in hours)
        
    Returns:
        DataFrame with lag features added
    """
    df = df.sort_values("observed_at").copy()
    
    for lag in lags:
        lag_col_name = f"{column}_lag_{lag}h"
        df[lag_col_name] = df[column].shift(lag)
    
    return df


def create_rolling_features(
    df: pd.DataFrame, column: str, windows: List[int], agg_funcs: List[str]
) -> pd.DataFrame:
    """Create rolling window features.
    
    Args:
        df: DataFrame with time series data
        column: Column name to aggregate
        windows: List of window sizes (in hours)
        agg_funcs: List of aggregation functions ('mean', 'std', 'min', 'max')
        
    Returns:
        DataFrame with rolling features added
    """
    df = df.sort_values("observed_at").copy()
    
    for window in windows:
        for agg_func in agg_funcs:
            col_name = f"{column}_rolling_{agg_func}_{window}h"
            
            if agg_func == "mean":
                df[col_name] = df[column].rolling(window=window, min_periods=1).mean()
            elif agg_func == "std":
                df[col_name] = df[column].rolling(window=window, min_periods=2).std()
            elif agg_func == "min":
                df[col_name] = df[column].rolling(window=window, min_periods=1).min()
            elif agg_func == "max":
                df[col_name] = df[column].rolling(window=window, min_periods=1).max()
    
    return df


def create_change_features(df: pd.DataFrame, column: str, periods: List[int]) -> pd.DataFrame:
    """Create change/difference features.
    
    Args:
        df: DataFrame with time series data
        column: Column name to compute changes for
        periods: List of periods to compute changes over (in hours)
        
    Returns:
        DataFrame with change features added
    """
    df = df.sort_values("observed_at").copy()
    
    for period in periods:
        change_col = f"{column}_change_{period}h"
        df[change_col] = df[column] - df[column].shift(period)
        
        # Rate of change
        if period == 1:
            rate_col = f"{column}_change_rate_{period}h"
            df[rate_col] = df[change_col] / (period + 1e-6)
    
    return df


def observations_to_features(observations: List[Observation]) -> pd.DataFrame:
    """Convert observations to feature vectors.
    
    Args:
        observations: List of observations
        
    Returns:
        DataFrame with engineered features
    """
    if not observations:
        return pd.DataFrame()
    
    # Convert to DataFrame
    data = []
    for obs in observations:
        row = {
            "location_id": obs.location_id,
            "observed_at": obs.observed_at,
            "aqi": obs.aqi,
            "pm25": obs.pm25,
            "pm10": obs.pm10,
            "o3": obs.o3,
            "no2": obs.no2,
            "so2": obs.so2,
            "co": obs.co,
            "temperature_c": obs.temperature_c,
            "humidity_pct": obs.humidity_pct,
            "pressure_hpa": obs.pressure_hpa,
            "wind_speed_ms": obs.wind_speed_ms,
            "wind_direction_deg": obs.wind_direction_deg,
            "cloud_pct": obs.cloud_pct,
            "precipitation_mm": obs.precipitation_mm,
            "missing_field_count": obs.missing_field_count,
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.sort_values("observed_at").reset_index(drop=True)
    
    # Add time features
    time_features = df["observed_at"].apply(create_time_features)
    time_df = pd.DataFrame(time_features.tolist())
    df = pd.concat([df, time_df], axis=1)
    
    # Add weather features (wind direction sin/cos)
    wind_dir_rad = df["wind_direction_deg"].apply(
        lambda x: math.radians(x) if pd.notna(x) else None
    )
    df["wind_direction_sin"] = wind_dir_rad.apply(
        lambda x: math.sin(x) if x is not None else None
    )
    df["wind_direction_cos"] = wind_dir_rad.apply(
        lambda x: math.cos(x) if x is not None else None
    )
    
    # Create lag features
    df = create_lag_features(df, "aqi", [1, 3, 6, 12, 24])
    df = create_lag_features(df, "pm25", [1, 3, 6])
    
    # Create rolling features
    df = create_rolling_features(df, "aqi", [3, 6, 12, 24], ["mean", "std", "min", "max"])
    
    # Create change features
    df = create_change_features(df, "aqi", [1, 3])
    df = create_change_features(df, "pm25", [1])
    
    # Data quality features
    df["imputation_flag"] = False
    df["hours_since_observation"] = 0.0
    
    # Rename aqi to aqi_current
    df = df.rename(columns={"aqi": "aqi_current"})
    
    logger.info(
        "Created features",
        rows=len(df),
        features=len(df.columns),
        location=df["location_id"].iloc[0] if len(df) > 0 else None,
    )
    
    return df


def create_targets(df: pd.DataFrame, horizon_days: int = 3, aggregation: str = "mean") -> pd.DataFrame:
    """Create target variables for supervised learning.
    
    Args:
        df: DataFrame with features and aqi_current
        horizon_days: Number of days to forecast
        aggregation: How to aggregate hourly to daily ('mean', 'max', 'median')
        
    Returns:
        DataFrame with target columns added
    """
    df = df.copy()
    
    # Ensure datetime index
    df = df.sort_values("observed_at").reset_index(drop=True)
    df["date"] = df["observed_at"].dt.date
    
    # Create future targets
    for day in range(1, horizon_days + 1):
        target_col = f"target_aqi_day_{day}"
        
        # Shift dates by day offset
        future_df = df.copy()
        future_df["target_date"] = pd.to_datetime(future_df["date"]) + pd.Timedelta(days=day)
        future_df["target_date"] = future_df["target_date"].dt.date
        
        # Aggregate AQI by date
        if aggregation == "mean":
            daily_aqi = df.groupby("date")["aqi_current"].mean()
        elif aggregation == "max":
            daily_aqi = df.groupby("date")["aqi_current"].max()
        elif aggregation == "median":
            daily_aqi = df.groupby("date")["aqi_current"].median()
        else:
            daily_aqi = df.groupby("date")["aqi_current"].mean()
        
        # Map future targets
        df[target_col] = df["observed_at"].apply(
            lambda x: daily_aqi.get((x + pd.Timedelta(days=day)).date(), None)
        )
    
    logger.info(
        "Created targets",
        horizon_days=horizon_days,
        aggregation=aggregation,
        rows_with_targets=df["target_aqi_day_1"].notna().sum(),
    )
    
    return df


def get_feature_columns() -> List[str]:
    """Get list of feature column names for modeling.
    
    Returns:
        List of feature column names
    """
    features = [
        # Time features
        "hour", "day_of_week", "day_of_month", "month", "week_of_year",
        "is_weekend", "hour_sin", "hour_cos", "month_sin", "month_cos",
        # Current pollutants
        "aqi_current", "pm25", "pm10", "o3", "no2", "so2", "co",
        # Weather
        "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_ms",
        "wind_direction_sin", "wind_direction_cos", "cloud_pct", "precipitation_mm",
        # Lags
        "aqi_lag_1h", "aqi_lag_3h", "aqi_lag_6h", "aqi_lag_12h", "aqi_lag_24h",
        "pm25_lag_1h", "pm25_lag_3h", "pm25_lag_6h",
        # Rolling stats
        "aqi_rolling_mean_3h", "aqi_rolling_mean_6h", "aqi_rolling_mean_12h", "aqi_rolling_mean_24h",
        "aqi_rolling_std_3h", "aqi_rolling_std_12h",
        "aqi_rolling_min_12h", "aqi_rolling_max_12h",
        # Changes
        "aqi_change_1h", "aqi_change_3h", "aqi_change_rate_1h", "pm25_change_1h",
        # Data quality
        "missing_field_count",
    ]
    
    return features


def get_target_columns(horizon_days: int = 3) -> List[str]:
    """Get list of target column names.
    
    Args:
        horizon_days: Number of forecast days
        
    Returns:
        List of target column names
    """
    return [f"target_aqi_day_{day}" for day in range(1, horizon_days + 1)]
