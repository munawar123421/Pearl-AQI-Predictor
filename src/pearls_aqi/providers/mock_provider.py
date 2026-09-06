"""Mock data provider for demo mode."""

import hashlib
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List

from pearls_aqi.logging_config import get_logger
from pearls_aqi.providers.base import DataProvider
from pearls_aqi.schemas import Location, Observation

logger = get_logger(__name__)


class MockProvider(DataProvider):
    """Mock provider generating deterministic synthetic data."""

    def __init__(self, seed: int = 42):
        """Initialize mock provider with random seed.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        random.seed(seed)

    def fetch_current(self, location: Location) -> Observation:
        """Generate current synthetic observation."""
        now = datetime.now(timezone.utc)
        return self._generate_observation(location, now, is_forecast=False)

    def fetch_historical(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[Observation]:
        """Generate historical synthetic observations."""
        observations = []
        current_time = start_time

        while current_time <= end_time:
            obs = self._generate_observation(location, current_time, is_forecast=False)
            observations.append(obs)
            current_time += timedelta(hours=1)

        logger.info(
            "Generated historical data",
            location=location.location_id,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
            count=len(observations),
        )

        return observations

    def fetch_forecast(self, location: Location, horizon_days: int = 3) -> List[Observation]:
        """Generate forecast synthetic observations."""
        observations = []
        now = datetime.now(timezone.utc)

        for day in range(1, horizon_days + 1):
            forecast_time = now + timedelta(days=day)
            obs = self._generate_observation(location, forecast_time, is_forecast=True)
            observations.append(obs)

        return observations

    def _generate_observation(
        self, location: Location, obs_time: datetime, is_forecast: bool = False
    ) -> Observation:
        """Generate a single synthetic observation.
        
        Uses deterministic patterns based on time and location to create
        realistic-looking data with daily and seasonal variations.
        """
        # Use location and time to seed variation
        seed_val = (
            hash(location.location_id)
            + obs_time.year * 10000
            + obs_time.month * 100
            + obs_time.day
            + obs_time.hour
        )
        random.seed(seed_val)

        # Time-based patterns
        hour = obs_time.hour
        day_of_year = obs_time.timetuple().tm_yday
        
        # Base AQI with daily and seasonal patterns
        base_aqi = 80 + 30 * math.sin(2 * math.pi * day_of_year / 365)
        daily_variation = 20 * math.sin(2 * math.pi * hour / 24)
        rush_hour_spike = 15 if hour in [8, 9, 18, 19] else 0
        aqi = base_aqi + daily_variation + rush_hour_spike + random.gauss(0, 10)
        aqi = max(10, min(300, aqi))  # Clamp to reasonable range

        # PM2.5 correlated with AQI
        pm25 = aqi * 0.4 + random.gauss(0, 5)
        pm25 = max(0, pm25)

        # PM10 typically higher than PM2.5
        pm10 = pm25 * 1.6 + random.gauss(0, 8)
        pm10 = max(0, pm10)

        # Other pollutants
        o3 = 30 + 20 * math.sin(2 * math.pi * hour / 24) + random.gauss(0, 5)
        o3 = max(0, o3)

        no2 = 20 + 10 * (1 if hour in [7, 8, 9, 17, 18, 19] else 0) + random.gauss(0, 3)
        no2 = max(0, no2)

        so2 = 10 + random.gauss(0, 2)
        so2 = max(0, so2)

        co = 0.5 + random.gauss(0, 0.1)
        co = max(0, co)

        # Weather patterns
        # Temperature varies by season and time of day
        base_temp = 20 + 10 * math.sin(2 * math.pi * day_of_year / 365)
        daily_temp_var = 5 * math.sin(2 * math.pi * (hour - 6) / 24)
        temperature = base_temp + daily_temp_var + random.gauss(0, 2)

        humidity = 60 + 20 * math.sin(2 * math.pi * day_of_year / 365) + random.gauss(0, 10)
        humidity = max(20, min(95, humidity))

        pressure = 1013 + random.gauss(0, 5)

        wind_speed = 2 + abs(random.gauss(0, 1))
        wind_direction = random.uniform(0, 360)

        cloud_pct = max(0, min(100, random.gauss(50, 25)))
        precipitation = max(0, random.expovariate(10) if cloud_pct > 70 else 0)

        # Create payload hash for deduplication
        payload_str = f"{location.location_id}_{obs_time.isoformat()}_{aqi}"
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()

        # Count missing fields (mock has none)
        missing_count = 0

        observation = Observation(
            location_id=location.location_id,
            city=location.city,
            country=location.country,
            latitude=location.latitude,
            longitude=location.longitude,
            source="mock",
            observed_at=obs_time,
            retrieved_at=datetime.now(timezone.utc),
            timezone=location.timezone,
            aqi=round(aqi, 1),
            pm25=round(pm25, 1),
            pm10=round(pm10, 1),
            o3=round(o3, 1),
            no2=round(no2, 1),
            so2=round(so2, 1),
            co=round(co, 2),
            temperature_c=round(temperature, 1),
            humidity_pct=round(humidity, 0),
            pressure_hpa=round(pressure, 1),
            wind_speed_ms=round(wind_speed, 1),
            wind_direction_deg=round(wind_direction, 0),
            precipitation_mm=round(precipitation, 1),
            cloud_pct=round(cloud_pct, 0),
            is_observed=not is_forecast,
            is_forecast=is_forecast,
            missing_field_count=missing_count,
            data_quality_flag="excellent",
            raw_payload_hash=payload_hash,
        )

        return observation

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "mock"

    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate mock provider configuration (always valid)."""
        return True, []
