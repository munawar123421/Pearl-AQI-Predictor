"""Backfill historical data script."""

import argparse
from datetime import datetime, timedelta, timezone

import yaml

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.features.transform import create_targets, observations_to_features
from pearls_aqi.ingestion.fetch_data import (
    deduplicate_observations,
    get_provider,
    observations_to_dataframe,
    save_raw_observation,
)
from pearls_aqi.logging_config import get_logger
from pearls_aqi.schemas import Location
from pearls_aqi.settings import PROJECT_ROOT, settings

logger = get_logger(__name__)


def load_location(city: str) -> Location:
    """Load location configuration from YAML."""
    locations_file = PROJECT_ROOT / "configs" / "locations.yaml"
    
    with open(locations_file, "r") as f:
        data = yaml.safe_load(f)
    
    for loc_data in data.get("locations", []):
        if loc_data.get("city", "").lower() == city.lower():
            return Location(**loc_data)
    
    raise ValueError(f"Location '{city}' not found in configuration")


def run_backfill(
    location: Location,
    start_date: str,
    end_date: str,
    interval_hours: int = 1,
    provider_name: str = None,
):
    """Run backfill for a location and date range.
    
    Args:
        location: Location configuration
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval_hours: Interval between observations
        provider_name: Data provider name
    """
    logger.info(
        "Starting backfill",
        location=location.location_id,
        start=start_date,
        end=end_date,
        interval_hours=interval_hours,
    )
    
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    # Get provider
    provider = get_provider(provider_name)
    
    # Fetch historical data
    logger.info(f"Fetching historical data from {provider.get_provider_name()}")
    
    observations = provider.fetch_historical(location, start_dt, end_dt)
    
    logger.info(f"Fetched {len(observations)} observations")
    
    # Deduplicate
    observations = deduplicate_observations(observations)
    
    # Save raw observations
    for obs in observations:
        save_raw_observation(obs)
    
    # Convert to features
    logger.info("Converting observations to features")
    features_df = observations_to_features(observations)
    
    # Create targets
    logger.info("Creating targets")
    features_df = create_targets(features_df, horizon_days=settings.forecast_horizon_days)
    
    # Save to feature store
    logger.info("Saving to feature store")
    feature_store = get_feature_store()
    
    obs_df = observations_to_dataframe(observations)
    feature_store.write_observations(obs_df)
    feature_store.write_features(features_df)
    
    # Summary
    rows_with_targets = features_df["target_aqi_day_1"].notna().sum()
    
    logger.info(
        "Backfill complete",
        location=location.location_id,
        observations=len(observations),
        feature_rows=len(features_df),
        training_rows=rows_with_targets,
    )
    
    print(f"\n✓ Backfill complete!")
    print(f"  Location: {location.city}, {location.country}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Observations: {len(observations)}")
    print(f"  Feature rows: {len(features_df)}")
    print(f"  Training rows: {rows_with_targets}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backfill historical AQI data")
    parser.add_argument("--city", type=str, default=settings.default_city, help="City name")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", type=int, default=1, help="Interval in hours")
    parser.add_argument("--provider", type=str, default=None, help="Data provider")
    parser.add_argument("--demo", action="store_true", help="Use demo mode")
    
    args = parser.parse_args()
    
    # Set demo mode if requested
    if args.demo:
        settings.demo_mode = True
        settings.data_provider = "mock"
    
    # Load location
    location = load_location(args.city)
    
    # Run backfill
    run_backfill(
        location=location,
        start_date=args.start,
        end_date=args.end,
        interval_hours=args.interval,
        provider_name=args.provider,
    )


if __name__ == "__main__":
    main()
