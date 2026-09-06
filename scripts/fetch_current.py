"""Fetch current air quality data."""

import argparse

import yaml

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.features.transform import observations_to_features
from pearls_aqi.ingestion.fetch_data import fetch_and_save_current, observations_to_dataframe
from pearls_aqi.logging_config import get_logger
from pearls_aqi.schemas import Location
from pearls_aqi.settings import PROJECT_ROOT, settings

logger = get_logger(__name__)


def load_locations() -> list:
    """Load locations from configuration."""
    locations_file = PROJECT_ROOT / "configs" / "locations.yaml"
    
    with open(locations_file, "r") as f:
        data = yaml.safe_load(f)
    
    locations = []
    for loc_data in data.get("locations", []):
        if loc_data.get("enabled", True):
            locations.append(Location(**loc_data))
    
    return locations


def fetch_and_store(location: Location):
    """Fetch current data and store in feature store."""
    logger.info(f"Fetching current data for {location.city}")
    
    # Fetch observation
    observation = fetch_and_save_current(location)
    
    # Convert to features
    features_df = observations_to_features([observation])
    
    # Store in feature store
    feature_store = get_feature_store()
    obs_df = observations_to_dataframe([observation])
    feature_store.write_observations(obs_df)
    feature_store.write_features(features_df)
    
    print(f"✓ {location.city}: AQI {observation.aqi}, PM2.5 {observation.pm25}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fetch current AQI data")
    parser.add_argument("--city", type=str, default=None, help="Specific city")
    parser.add_argument("--demo", action="store_true", help="Use demo mode")
    
    args = parser.parse_args()
    
    if args.demo:
        settings.demo_mode = True
        settings.data_provider = "mock"
    
    # Load locations
    locations = load_locations()
    
    if args.city:
        locations = [loc for loc in locations if loc.city.lower() == args.city.lower()]
        if not locations:
            print(f"✗ City '{args.city}' not found in configuration")
            return
    
    print(f"Fetching current data for {len(locations)} location(s)...\n")
    
    for location in locations:
        try:
            fetch_and_store(location)
        except Exception as e:
            logger.error(f"Failed to fetch {location.city}", error=str(e))
            print(f"✗ {location.city}: {str(e)}")


if __name__ == "__main__":
    main()
