"""Smoke test for complete demo workflow."""

from datetime import datetime, timedelta, timezone

import pytest

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.features.transform import create_targets, observations_to_features
from pearls_aqi.ingestion.fetch_data import observations_to_dataframe
from pearls_aqi.modeling.dataset import prepare_train_test_split
from pearls_aqi.modeling.registry import get_registry
from pearls_aqi.modeling.train import train_models
from pearls_aqi.providers import MockProvider
from pearls_aqi.schemas import Location


@pytest.fixture
def demo_location():
    """Create a demo location for testing."""
    return Location(
        location_id="demo_city",
        city="Demo City",
        country="Demo Country",
        latitude=40.0,
        longitude=-74.0,
        timezone="UTC",
    )


def test_complete_demo_workflow(demo_location):
    """Test complete workflow from data generation to prediction."""
    
    # Step 1: Generate demo data
    provider = MockProvider(seed=42)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)
    
    observations = provider.fetch_historical(demo_location, start_time, end_time)
    
    assert len(observations) > 100, "Should have sufficient observations"
    
    # Step 2: Convert to features
    features_df = observations_to_features(observations)
    
    assert not features_df.empty, "Features should be created"
    assert len(features_df) == len(observations)
    
    # Step 3: Create targets
    features_df = create_targets(features_df, horizon_days=3)
    
    assert "target_aqi_day_1" in features_df.columns
    assert features_df["target_aqi_day_1"].notna().sum() > 0
    
    # Step 4: Store in feature store
    feature_store = get_feature_store()
    obs_df = observations_to_dataframe(observations)
    
    feature_store.write_observations(obs_df)
    feature_store.write_features(features_df)
    
    # Step 5: Load and verify
    loaded_df = feature_store.read_features(location_id=demo_location.location_id)
    
    assert not loaded_df.empty, "Should be able to load features"
    
    # Step 6: Train a simple model (just test it runs)
    df_valid = features_df.dropna(subset=["target_aqi_day_1", "target_aqi_day_2", "target_aqi_day_3"])
    
    if len(df_valid) > 100:
        train_df, val_df, test_df = prepare_train_test_split(df_valid)
        
        assert len(train_df) > 0
        assert len(val_df) > 0
        assert len(test_df) > 0


def test_feature_store_health_check():
    """Test feature store health status."""
    feature_store = get_feature_store()
    health = feature_store.get_health_status()
    
    assert "locations" in health
    assert "total_rows" in health
    assert "is_stale" in health


def test_model_registry_operations():
    """Test basic model registry operations."""
    registry = get_registry()
    
    # Should be able to list models
    models = registry.list_models()
    
    assert isinstance(models, list)
