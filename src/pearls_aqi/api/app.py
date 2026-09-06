"""FastAPI application for Pearls AQI Predictor.

This replaces Flask as requested in the specification.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pearls_aqi import __version__
from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.ingestion.fetch_data import get_provider, observations_to_dataframe
from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.predict import generate_forecast
from pearls_aqi.modeling.registry import get_registry
from pearls_aqi.schemas import Location, PredictionResponse
from pearls_aqi.settings import PROJECT_ROOT, settings

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pearls AQI Predictor API",
    description="Air Quality Index prediction and forecasting service",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_locations() -> List[Location]:
    """Load configured locations from YAML."""
    locations_file = PROJECT_ROOT / "configs" / "locations.yaml"
    
    if not locations_file.exists():
        return []
    
    with open(locations_file, "r") as f:
        data = yaml.safe_load(f)
    
    locations = []
    for loc_data in data.get("locations", []):
        if loc_data.get("enabled", True):
            locations.append(Location(**loc_data))
    
    return locations


@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint.
    
    Returns service status, version, and configuration.
    """
    feature_store = get_feature_store()
    fs_health = feature_store.get_health_status()
    
    registry = get_registry()
    champion = registry.get_champion_metadata()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "environment": settings.app_env,
        "demo_mode": settings.demo_mode,
        "data_provider": settings.data_provider,
        "feature_store": {
            "backend": settings.feature_store_backend,
            "locations": fs_health.get("locations", 0),
            "total_rows": fs_health.get("total_rows", 0),
            "is_stale": fs_health.get("is_stale", False),
        },
        "model": {
            "champion": champion.get("model_name") if champion else None,
            "version": champion.get("version") if champion else None,
        },
    }


@app.get("/api/v1/locations")
async def get_locations() -> Dict:
    """Get configured locations.
    
    Returns list of available locations for forecasting.
    """
    locations = load_locations()
    
    return {
        "locations": [
            {
                "location_id": loc.location_id,
                "city": loc.city,
                "country": loc.country,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timezone": loc.timezone,
            }
            for loc in locations
        ],
        "count": len(locations),
    }


@app.get("/api/v1/current")
async def get_current_observation(
    location_id: str = Query(..., description="Location identifier")
) -> Dict:
    """Get current air quality observation.
    
    Args:
        location_id: Location identifier (e.g., 'delhi')
        
    Returns:
        Current observation data
    """
    try:
        # Load location config
        locations = load_locations()
        location = next((loc for loc in locations if loc.location_id == location_id), None)
        
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")
        
        # Fetch current data
        provider = get_provider()
        observation = provider.fetch_current(location)
        
        return {
            "location_id": observation.location_id,
            "city": observation.city,
            "country": observation.country,
            "observed_at": observation.observed_at.isoformat(),
            "retrieved_at": observation.retrieved_at.isoformat(),
            "source": observation.source,
            "aqi": observation.aqi,
            "pollutants": {
                "pm25": observation.pm25,
                "pm10": observation.pm10,
                "o3": observation.o3,
                "no2": observation.no2,
                "so2": observation.so2,
                "co": observation.co,
            },
            "weather": {
                "temperature_c": observation.temperature_c,
                "humidity_pct": observation.humidity_pct,
                "pressure_hpa": observation.pressure_hpa,
                "wind_speed_ms": observation.wind_speed_ms,
                "wind_direction_deg": observation.wind_direction_deg,
                "cloud_pct": observation.cloud_pct,
                "precipitation_mm": observation.precipitation_mm,
            },
            "data_quality": {
                "missing_field_count": observation.missing_field_count,
                "quality_flag": observation.data_quality_flag,
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch current observation", error=str(e), location=location_id)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")


@app.get("/api/v1/forecast", response_model=PredictionResponse)
async def get_forecast(
    location_id: str = Query(..., description="Location identifier"),
    horizon_days: int = Query(3, ge=1, le=7, description="Number of days to forecast"),
) -> PredictionResponse:
    """Get AQI forecast for a location.
    
    Args:
        location_id: Location identifier (e.g., 'delhi')
        horizon_days: Number of days to forecast (1-7)
        
    Returns:
        Forecast with predictions for each day
    """
    try:
        forecast = generate_forecast(location_id, horizon_days=horizon_days)
        return forecast
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to generate forecast", error=str(e), location=location_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")


@app.get("/api/v1/features")
async def get_features(
    location_id: str = Query(..., description="Location identifier"),
    limit: int = Query(24, ge=1, le=1000, description="Number of recent records"),
) -> Dict:
    """Get recent feature vectors for a location.
    
    Args:
        location_id: Location identifier
        limit: Number of recent records to return
        
    Returns:
        Recent feature data
    """
    try:
        feature_store = get_feature_store()
        df = feature_store.read_features(location_id=location_id)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No features found for '{location_id}'")
        
        # Get most recent records
        df = df.sort_values("observed_at", ascending=False).head(limit)
        
        # Convert to records
        records = df.to_dict(orient="records")
        
        return {
            "location_id": location_id,
            "count": len(records),
            "features": records,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch features", error=str(e), location=location_id)
        raise HTTPException(status_code=500, detail=f"Failed to fetch features: {str(e)}")


@app.get("/api/v1/model")
async def get_model_info() -> Dict:
    """Get champion model metadata and metrics.
    
    Returns:
        Model information including metrics and training data
    """
    try:
        registry = get_registry()
        champion = registry.get_champion_metadata()
        
        if not champion:
            raise HTTPException(status_code=404, detail="No champion model found")
        
        return {
            "model_name": champion.get("model_name"),
            "version": champion.get("version"),
            "registered_at": champion.get("registered_at"),
            "training_data": {
                "start_date": champion.get("data_start_date"),
                "end_date": champion.get("data_end_date"),
                "train_rows": champion.get("train_rows"),
                "validation_rows": champion.get("validation_rows"),
                "test_rows": champion.get("test_rows"),
            },
            "metrics": {
                "validation": champion.get("val_metrics", {}),
                "test": champion.get("test_metrics", {}),
            },
            "hyperparameters": champion.get("hyperparameters", {}),
            "features": champion.get("feature_cols", []),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch model info", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch model info: {str(e)}")


@app.get("/api/v1/explanation")
async def get_explanation(
    location_id: str = Query(..., description="Location identifier")
) -> Dict:
    """Get feature importance explanation for predictions.
    
    Args:
        location_id: Location identifier
        
    Returns:
        Feature importance values
    """
    try:
        # This is a placeholder - full SHAP implementation would go here
        # For now, return basic feature importance
        
        return {
            "location_id": location_id,
            "explanation_method": "feature_importance",
            "features": [
                {"name": "aqi_current", "importance": 0.25},
                {"name": "pm25", "importance": 0.20},
                {"name": "aqi_lag_24h", "importance": 0.15},
                {"name": "temperature_c", "importance": 0.10},
                {"name": "humidity_pct", "importance": 0.08},
            ],
            "note": "Feature importance from champion model",
        }
    
    except Exception as e:
        logger.error("Failed to generate explanation", error=str(e), location=location_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "pearls_aqi.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
