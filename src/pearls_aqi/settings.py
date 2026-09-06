"""Configuration settings for Pearls AQI Predictor."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = "development"
    demo_mode: bool = True
    log_level: str = "INFO"

    # Default Location
    default_city: str = "Karachi"
    default_country: str = "Pakistan"
    default_latitude: float = 24.8607
    default_longitude: float = 67.0011
    timezone: str = "UTC"

    # Data Provider
    data_provider: str = "mock"

    # AQICN API
    aqicn_token: Optional[str] = None
    aqicn_station: Optional[str] = None

    # OpenWeather API
    openweather_api_key: Optional[str] = None
    openweather_latitude: Optional[float] = None
    openweather_longitude: Optional[float] = None

    # Feature Store
    feature_store_backend: str = "local"
    feature_store_path: str = "data/features"

    # Model Registry
    model_registry_path: str = "data/models"

    # Data Paths
    raw_data_path: str = "data/raw"
    processed_data_path: str = "data/processed"
    reports_path: str = "data/reports"

    # Forecasting
    forecast_horizon_days: int = 3

    # Alert Thresholds
    pollution_alert_aqi: int = 150
    hazardous_aqi: int = 300

    # Training
    min_training_rows: int = 168
    train_test_split: float = 0.70
    validation_split: float = 0.15
    test_split: float = 0.15

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Dashboard
    dashboard_port: int = 8501

    # Request Configuration
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: int = 2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute path from project root."""
        return PROJECT_ROOT / relative_path

    @property
    def feature_store_absolute_path(self) -> Path:
        """Get absolute feature store path."""
        return self.get_absolute_path(self.feature_store_path)

    @property
    def model_registry_absolute_path(self) -> Path:
        """Get absolute model registry path."""
        return self.get_absolute_path(self.model_registry_path)

    @property
    def raw_data_absolute_path(self) -> Path:
        """Get absolute raw data path."""
        return self.get_absolute_path(self.raw_data_path)

    @property
    def processed_data_absolute_path(self) -> Path:
        """Get absolute processed data path."""
        return self.get_absolute_path(self.processed_data_path)

    @property
    def reports_absolute_path(self) -> Path:
        """Get absolute reports path."""
        return self.get_absolute_path(self.reports_path)

    def validate_real_mode_config(self) -> tuple[bool, list[str]]:
        """Validate configuration for real API mode.
        
        Returns:
            Tuple of (is_valid, list of missing required fields)
        """
        if self.demo_mode:
            return True, []

        missing = []

        if self.data_provider == "aqicn":
            if not self.aqicn_token:
                missing.append("AQICN_TOKEN")
            if not self.aqicn_station:
                missing.append("AQICN_STATION")

        elif self.data_provider == "openweather":
            if not self.openweather_api_key:
                missing.append("OPENWEATHER_API_KEY")
            if self.openweather_latitude is None:
                missing.append("OPENWEATHER_LATITUDE")
            if self.openweather_longitude is None:
                missing.append("OPENWEATHER_LONGITUDE")

        return len(missing) == 0, missing


# Global settings instance
settings = Settings()


def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        settings.feature_store_absolute_path,
        settings.model_registry_absolute_path,
        settings.raw_data_absolute_path,
        settings.processed_data_absolute_path,
        settings.reports_absolute_path,
        settings.reports_absolute_path / "eda",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Ensure directories on import
ensure_directories()
