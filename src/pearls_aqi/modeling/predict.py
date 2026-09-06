"""Prediction service for generating forecasts."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.dataset import prepare_model_inputs
from pearls_aqi.modeling.registry import get_registry
from pearls_aqi.schemas import Forecast, PredictionResponse, get_aqi_category
from pearls_aqi.settings import settings

logger = get_logger(__name__)


def generate_forecast(
    location_id: str,
    model_version: str = "champion",
    horizon_days: int = 3,
) -> PredictionResponse:
    """Generate AQI forecast for a location.
    
    Args:
        location_id: Location identifier
        model_version: Model version to use ('champion' or specific version)
        horizon_days: Number of days to forecast
        
    Returns:
        PredictionResponse with forecasts
    """
    # Load champion model
    registry = get_registry()
    model_artifacts = registry.load_model(model_version)
    
    model = model_artifacts["model"]
    scaler = model_artifacts["scaler"]
    metadata = model_artifacts["metadata"]
    
    # Get latest features
    feature_store = get_feature_store()
    latest_features = feature_store.get_latest_features(location_id)
    
    if latest_features is None:
        raise ValueError(f"No features found for location: {location_id}")
    
    # Prepare input
    feature_cols = metadata.get("feature_cols", [])
    df_input = pd.DataFrame([latest_features])
    
    X, _, _ = prepare_model_inputs(
        df_input,
        feature_cols,
        target_cols=[],
        fit_scaler=False,
        scaler=scaler,
    )
    
    if len(X) == 0:
        raise ValueError(f"Could not prepare features for location: {location_id}")
    
    # Generate predictions
    predictions = model.predict(X)[0]  # Shape: [n_horizons]
    
    # Clip negative predictions
    predictions = np.maximum(predictions, 0)
    
    # Create forecast objects
    forecasts = []
    base_date = datetime.now(timezone.utc).date()
    
    for i in range(min(horizon_days, len(predictions))):
        forecast_date = base_date + timedelta(days=i + 1)
        aqi_value = float(predictions[i])
        
        # Estimate uncertainty (simple approach using +/- 20%)
        lower = max(0, aqi_value * 0.8)
        upper = aqi_value * 1.2
        
        # Get category
        category_info = get_aqi_category(aqi_value)
        
        forecast = Forecast(
            date=forecast_date.isoformat(),
            aqi=round(aqi_value, 1),
            lower=round(lower, 1),
            upper=round(upper, 1),
            category=category_info.name,
            health_message=category_info.health_message,
        )
        forecasts.append(forecast)
    
    # Data quality info
    hours_since_obs = (
        (datetime.now(timezone.utc) - latest_features["observed_at"].to_pydatetime()).total_seconds()
        / 3600
    )
    
    data_quality = {
        "latest_observation_at": latest_features["observed_at"].isoformat(),
        "hours_since_observation": round(hours_since_obs, 1),
        "missing_feature_count": int(latest_features.get("missing_field_count", 0)),
    }
    
    # Alert logic
    alert = None
    max_forecast_aqi = max(f.aqi for f in forecasts)
    
    if max_forecast_aqi >= settings.hazardous_aqi:
        alert = {
            "level": "hazardous",
            "message": f"Hazardous AQI forecast: {round(max_forecast_aqi, 0)}. Avoid outdoor activities.",
        }
    elif max_forecast_aqi >= settings.pollution_alert_aqi:
        alert = {
            "level": "warning",
            "message": f"Unhealthy AQI forecast: {round(max_forecast_aqi, 0)}. Sensitive groups should limit outdoor exposure.",
        }
    
    # Build response
    response = PredictionResponse(
        location={
            "location_id": location_id,
            "city": latest_features.get("location_id", location_id).title(),
        },
        generated_at=datetime.now(timezone.utc),
        model={
            "name": metadata.get("model_name", "unknown"),
            "version": metadata.get("version", "unknown"),
            "metrics": metadata.get("val_metrics", {}),
        },
        forecast=forecasts,
        data_quality=data_quality,
        alert=alert,
    )
    
    logger.info(
        "Generated forecast",
        location=location_id,
        model=metadata.get("model_name"),
        forecast_days=len(forecasts),
        max_aqi=round(max_forecast_aqi, 1),
    )
    
    return response
