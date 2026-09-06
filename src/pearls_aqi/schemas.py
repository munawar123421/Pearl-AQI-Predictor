"""Data schemas and validation models for Pearls AQI Predictor."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Location configuration."""

    location_id: str
    city: str
    country: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "UTC"
    aqicn_station: Optional[str] = None
    enabled: bool = True


class Observation(BaseModel):
    """Normalized observation from any data provider."""

    # Identity
    location_id: str
    city: str
    country: str
    latitude: float
    longitude: float
    source: str  # "aqicn", "openweather", "mock"

    # Time
    observed_at: datetime
    retrieved_at: datetime
    timezone: str = "UTC"

    # Target and pollutants
    aqi: Optional[float] = None
    pm25: Optional[float] = Field(None, ge=0)
    pm10: Optional[float] = Field(None, ge=0)
    o3: Optional[float] = Field(None, ge=0)
    no2: Optional[float] = Field(None, ge=0)
    so2: Optional[float] = Field(None, ge=0)
    co: Optional[float] = Field(None, ge=0)

    # Weather
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    pressure_hpa: Optional[float] = Field(None, ge=0)
    wind_speed_ms: Optional[float] = Field(None, ge=0)
    wind_direction_deg: Optional[float] = Field(None, ge=0, lt=360)
    precipitation_mm: Optional[float] = Field(None, ge=0)
    cloud_pct: Optional[float] = Field(None, ge=0, le=100)

    # Quality
    is_observed: bool = True
    is_forecast: bool = False
    missing_field_count: int = 0
    data_quality_flag: Optional[str] = None

    # Metadata
    raw_payload_hash: Optional[str] = None

    @field_validator("observed_at", "retrieved_at")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""
        if v.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware")
        return v

    def count_missing_fields(self) -> int:
        """Count number of missing optional fields."""
        pollutant_fields = ["pm25", "pm10", "o3", "no2", "so2", "co"]
        weather_fields = [
            "temperature_c",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_direction_deg",
            "precipitation_mm",
            "cloud_pct",
        ]

        missing = 0
        for field in pollutant_fields + weather_fields:
            if getattr(self, field) is None:
                missing += 1

        return missing

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class FeatureVector(BaseModel):
    """Feature vector for model training/inference."""

    # Identity and Time
    location_id: str
    event_time: datetime
    hour: int = Field(ge=0, lt=24)
    day_of_week: int = Field(ge=0, lt=7)
    day_of_month: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    week_of_year: int = Field(ge=1, le=53)
    is_weekend: bool
    hour_sin: float
    hour_cos: float
    month_sin: float
    month_cos: float

    # Current pollutants
    aqi_current: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    o3: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None

    # Weather
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_sin: Optional[float] = None
    wind_direction_cos: Optional[float] = None
    cloud_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None

    # Lags
    aqi_lag_1h: Optional[float] = None
    aqi_lag_3h: Optional[float] = None
    aqi_lag_6h: Optional[float] = None
    aqi_lag_12h: Optional[float] = None
    aqi_lag_24h: Optional[float] = None
    pm25_lag_1h: Optional[float] = None
    pm25_lag_3h: Optional[float] = None
    pm25_lag_6h: Optional[float] = None

    # Rolling statistics
    aqi_rolling_mean_3h: Optional[float] = None
    aqi_rolling_mean_6h: Optional[float] = None
    aqi_rolling_mean_12h: Optional[float] = None
    aqi_rolling_mean_24h: Optional[float] = None
    aqi_rolling_std_3h: Optional[float] = None
    aqi_rolling_std_12h: Optional[float] = None
    aqi_rolling_min_12h: Optional[float] = None
    aqi_rolling_max_12h: Optional[float] = None

    # Change features
    aqi_change_1h: Optional[float] = None
    aqi_change_3h: Optional[float] = None
    aqi_change_rate_1h: Optional[float] = None
    pm25_change_1h: Optional[float] = None

    # Data quality
    missing_field_count: int = 0
    imputation_flag: bool = False
    source_reliability_flag: Optional[str] = None
    hours_since_observation: Optional[float] = None

    # Targets (for training)
    target_aqi_day_1: Optional[float] = None
    target_aqi_day_2: Optional[float] = None
    target_aqi_day_3: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Forecast(BaseModel):
    """AQI forecast for a single day."""

    date: str
    aqi: float
    lower: Optional[float] = None
    upper: Optional[float] = None
    category: str
    health_message: Optional[str] = None


class PredictionResponse(BaseModel):
    """Complete prediction response."""

    location: Dict[str, str]
    generated_at: datetime
    model: Dict[str, Any]
    forecast: List[Forecast]
    data_quality: Dict[str, Any]
    alert: Optional[Dict[str, str]] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelMetadata(BaseModel):
    """Model registry metadata."""

    model_name: str
    version: str
    training_timestamp: datetime
    data_start_date: str
    data_end_date: str
    train_rows: int
    validation_rows: int
    test_rows: int
    features: List[str]
    metrics: Dict[str, float]
    hyperparameters: Dict[str, Any]
    git_commit: Optional[str] = None
    feature_store_schema_version: str = "1.0"
    is_champion: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DataQualityReport(BaseModel):
    """Data quality check report."""

    location_id: str
    check_timestamp: datetime
    total_rows: int
    duplicate_rows: int
    null_rate_by_field: Dict[str, float]
    latest_observation_time: Optional[datetime] = None
    hours_since_latest: Optional[float] = None
    is_stale: bool
    quality_score: float = Field(ge=0, le=1)
    warnings: List[str] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PipelineStatus(BaseModel):
    """Pipeline execution status."""

    pipeline_name: str
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str  # "running", "success", "failed"
    location_id: Optional[str] = None
    rows_processed: int = 0
    rows_rejected: int = 0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = {}

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AQICategory(BaseModel):
    """AQI category definition."""

    name: str
    min: int
    max: int
    color: str
    health_message: str


def get_aqi_category(aqi_value: float) -> AQICategory:
    """Get AQI category for a given AQI value.
    
    Based on US EPA AQI scale.
    """
    categories = [
        AQICategory(
            name="Good",
            min=0,
            max=50,
            color="green",
            health_message="Air quality is satisfactory",
        ),
        AQICategory(
            name="Moderate",
            min=51,
            max=100,
            color="yellow",
            health_message="Air quality is acceptable",
        ),
        AQICategory(
            name="Unhealthy for Sensitive Groups",
            min=101,
            max=150,
            color="orange",
            health_message="Sensitive groups may experience health effects",
        ),
        AQICategory(
            name="Unhealthy",
            min=151,
            max=200,
            color="red",
            health_message="Everyone may begin to experience health effects",
        ),
        AQICategory(
            name="Very Unhealthy",
            min=201,
            max=300,
            color="purple",
            health_message="Health alert: everyone may experience serious effects",
        ),
        AQICategory(
            name="Hazardous",
            min=301,
            max=500,
            color="maroon",
            health_message="Health warning: emergency conditions",
        ),
    ]

    for category in categories:
        if category.min <= aqi_value <= category.max:
            return category

    # Handle values outside normal range
    if aqi_value < 0:
        return categories[0]
    return categories[-1]
