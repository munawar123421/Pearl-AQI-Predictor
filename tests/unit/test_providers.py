"""Unit tests for data providers."""

from datetime import datetime, timedelta, timezone

import pytest

from pearls_aqi.providers import MockProvider
from pearls_aqi.schemas import Location


@pytest.fixture
def test_location():
    """Create a test location."""
    return Location(
        location_id="test_city",
        city="Test City",
        country="Test Country",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="UTC",
    )


def test_mock_provider_current(test_location):
    """Test mock provider current data fetch."""
    provider = MockProvider(seed=42)
    
    obs = provider.fetch_current(test_location)
    
    assert obs.location_id == "test_city"
    assert obs.source == "mock"
    assert obs.aqi is not None
    assert obs.aqi > 0
    assert obs.pm25 is not None


def test_mock_provider_historical(test_location):
    """Test mock provider historical data fetch."""
    provider = MockProvider(seed=42)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    observations = provider.fetch_historical(test_location, start_time, end_time)
    
    assert len(observations) > 0
    assert all(obs.source == "mock" for obs in observations)
    assert all(obs.location_id == "test_city" for obs in observations)


def test_mock_provider_forecast(test_location):
    """Test mock provider forecast."""
    provider = MockProvider(seed=42)
    
    forecasts = provider.fetch_forecast(test_location, horizon_days=3)
    
    assert len(forecasts) == 3
    assert all(obs.is_forecast for obs in forecasts)
    assert all(not obs.is_observed for obs in forecasts)


def test_mock_provider_deterministic(test_location):
    """Test that mock provider is deterministic with same seed."""
    provider1 = MockProvider(seed=42)
    provider2 = MockProvider(seed=42)
    
    obs1 = provider1.fetch_current(test_location)
    obs2 = provider2.fetch_current(test_location)
    
    # Should generate same values with same seed
    assert abs(obs1.aqi - obs2.aqi) < 0.1


def test_mock_provider_config_validation(test_location):
    """Test provider configuration validation."""
    provider = MockProvider()
    
    is_valid, errors = provider.validate_config()
    
    assert is_valid
    assert len(errors) == 0
