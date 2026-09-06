"""Data fetching and ingestion module."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd

from pearls_aqi.logging_config import get_logger
from pearls_aqi.providers import AQICNProvider, DataProvider, MockProvider, OpenWeatherProvider
from pearls_aqi.schemas import Location, Observation
from pearls_aqi.settings import settings

logger = get_logger(__name__)


def get_provider(provider_name: Optional[str] = None) -> DataProvider:
    """Get configured data provider.
    
    Args:
        provider_name: Provider name override (uses settings if None)
        
    Returns:
        Configured data provider instance
    """
    name = provider_name or settings.data_provider

    if name == "mock":
        return MockProvider()
    elif name == "aqicn":
        return AQICNProvider()
    elif name == "openweather":
        return OpenWeatherProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")


def save_raw_observation(observation: Observation, output_dir: Optional[Path] = None):
    """Save raw observation to disk.
    
    Args:
        observation: Observation to save
        output_dir: Output directory (uses settings if None)
    """
    if output_dir is None:
        output_dir = settings.raw_data_absolute_path

    # Create partitioned directory structure: source/location/date
    date_str = observation.observed_at.strftime("%Y-%m-%d")
    partition_dir = output_dir / observation.source / observation.location_id / date_str
    partition_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp_str = observation.observed_at.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp_str}_{observation.raw_payload_hash[:8]}.json"
    filepath = partition_dir / filename

    # Save as JSON
    with open(filepath, "w") as f:
        json.dump(observation.model_dump(mode="json"), f, indent=2, default=str)

    logger.debug("Saved raw observation", filepath=str(filepath))


def load_observations_from_disk(
    source: str, location_id: str, date_str: str, data_dir: Optional[Path] = None
) -> List[Observation]:
    """Load observations from disk for a specific date.
    
    Args:
        source: Data source name
        location_id: Location identifier
        date_str: Date string (YYYY-MM-DD)
        data_dir: Data directory (uses settings if None)
        
    Returns:
        List of loaded observations
    """
    if data_dir is None:
        data_dir = settings.raw_data_absolute_path

    partition_dir = data_dir / source / location_id / date_str

    if not partition_dir.exists():
        return []

    observations = []
    for filepath in partition_dir.glob("*.json"):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                obs = Observation(**data)
                observations.append(obs)
        except Exception as e:
            logger.warning("Failed to load observation", filepath=str(filepath), error=str(e))

    return observations


def deduplicate_observations(observations: List[Observation]) -> List[Observation]:
    """Remove duplicate observations based on location_id, observed_at, and source.
    
    Args:
        observations: List of observations
        
    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []

    for obs in observations:
        key = (obs.location_id, obs.observed_at.isoformat(), obs.source)
        if key not in seen:
            seen.add(key)
            unique.append(obs)

    if len(unique) < len(observations):
        logger.info(
            "Removed duplicates",
            original=len(observations),
            unique=len(unique),
            duplicates=len(observations) - len(unique),
        )

    return unique


def observations_to_dataframe(observations: List[Observation]) -> pd.DataFrame:
    """Convert list of observations to pandas DataFrame.
    
    Args:
        observations: List of observations
        
    Returns:
        DataFrame with observations
    """
    if not observations:
        return pd.DataFrame()

    # Convert to dicts
    data = [obs.model_dump() for obs in observations]
    df = pd.DataFrame(data)

    # Ensure datetime columns are parsed
    datetime_cols = ["observed_at", "retrieved_at"]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)

    # Sort by observed_at
    if "observed_at" in df.columns:
        df = df.sort_values("observed_at").reset_index(drop=True)

    return df


def validate_observation(observation: Observation) -> tuple[bool, List[str]]:
    """Validate an observation against data contract.
    
    Args:
        observation: Observation to validate
        
    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []

    # Check required fields
    if not observation.location_id:
        errors.append("location_id is required")
    
    if not observation.source:
        errors.append("source is required")

    # Check timezone awareness
    if observation.observed_at.tzinfo is None:
        errors.append("observed_at must be timezone-aware")
    
    if observation.retrieved_at.tzinfo is None:
        errors.append("retrieved_at must be timezone-aware")

    # Check value ranges
    if observation.humidity_pct is not None and not (0 <= observation.humidity_pct <= 100):
        errors.append(f"humidity_pct out of range: {observation.humidity_pct}")

    if observation.cloud_pct is not None and not (0 <= observation.cloud_pct <= 100):
        errors.append(f"cloud_pct out of range: {observation.cloud_pct}")

    # Check non-negative pollutants
    pollutants = ["pm25", "pm10", "o3", "no2", "so2", "co"]
    for pollutant in pollutants:
        value = getattr(observation, pollutant)
        if value is not None and value < 0:
            errors.append(f"{pollutant} cannot be negative: {value}")

    return len(errors) == 0, errors


def fetch_and_save_current(location: Location, provider: Optional[DataProvider] = None) -> Observation:
    """Fetch current observation and save to disk.
    
    Args:
        location: Location to fetch data for
        provider: Data provider (creates default if None)
        
    Returns:
        Fetched observation
    """
    if provider is None:
        provider = get_provider()

    logger.info(
        "Fetching current observation",
        location=location.location_id,
        provider=provider.get_provider_name(),
    )

    observation = provider.fetch_current(location)

    # Validate
    is_valid, errors = validate_observation(observation)
    if not is_valid:
        logger.warning("Observation validation failed", errors=errors, location=location.location_id)

    # Save raw data
    save_raw_observation(observation)

    logger.info(
        "Fetched current observation",
        location=location.location_id,
        aqi=observation.aqi,
        pm25=observation.pm25,
        missing_fields=observation.missing_field_count,
    )

    return observation
