"""Unit tests for data schemas."""

from datetime import datetime, timezone

import pytest

from pearls_aqi.schemas import Observation, get_aqi_category


def test_observation_creation():
    """Test creating a valid observation."""
    obs = Observation(
        location_id="test_loc",
        city="Test City",
        country="Test Country",
        latitude=40.7128,
        longitude=-74.0060,
        source="mock",
        observed_at=datetime.now(timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        timezone="UTC",
        aqi=75.0,
        pm25=25.0,
    )
    
    assert obs.location_id == "test_loc"
    assert obs.aqi == 75.0
    assert obs.pm25 == 25.0


def test_aqi_categories():
    """Test AQI category classification."""
    # Good
    category = get_aqi_category(25)
    assert category.name == "Good"
    assert category.color == "green"
    
    # Moderate
    category = get_aqi_category(75)
    assert category.name == "Moderate"
    assert category.color == "yellow"
    
    # Unhealthy for Sensitive Groups
    category = get_aqi_category(125)
    assert category.name == "Unhealthy for Sensitive Groups"
    assert category.color == "orange"
    
    # Unhealthy
    category = get_aqi_category(175)
    assert category.name == "Unhealthy"
    assert category.color == "red"
    
    # Very Unhealthy
    category = get_aqi_category(250)
    assert category.name == "Very Unhealthy"
    assert category.color == "purple"
    
    # Hazardous
    category = get_aqi_category(350)
    assert category.name == "Hazardous"
    assert category.color == "maroon"


def test_observation_validation():
    """Test observation data validation."""
    # Valid observation
    obs = Observation(
        location_id="test",
        city="Test",
        country="Country",
        latitude=0.0,
        longitude=0.0,
        source="mock",
        observed_at=datetime.now(timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        humidity_pct=50.0,
        pm25=10.0,
    )
    
    assert obs.humidity_pct == 50.0
    assert obs.pm25 == 10.0


def test_missing_field_count():
    """Test counting missing fields."""
    obs = Observation(
        location_id="test",
        city="Test",
        country="Country",
        latitude=0.0,
        longitude=0.0,
        source="mock",
        observed_at=datetime.now(timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        aqi=100.0,
        pm25=None,
        pm10=None,
        temperature_c=None,
    )
    
    missing = obs.count_missing_fields()
    assert missing > 0
