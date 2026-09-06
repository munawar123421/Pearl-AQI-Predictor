"""OpenWeather data provider implementation."""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pearls_aqi.logging_config import get_logger
from pearls_aqi.providers.base import DataProvider
from pearls_aqi.schemas import Location, Observation
from pearls_aqi.settings import settings

logger = get_logger(__name__)


class OpenWeatherProvider(DataProvider):
    """OpenWeather data provider for weather and air quality."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    AIR_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenWeather provider.
        
        Args:
            api_key: OpenWeather API key (from settings if not provided)
        """
        self.api_key = api_key or settings.openweather_api_key
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=settings.max_retries,
            backoff_factor=settings.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def fetch_current(self, location: Location) -> Observation:
        """Fetch current weather and air quality from OpenWeather."""
        is_valid, errors = self.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid OpenWeather configuration: {', '.join(errors)}")

        # Fetch air pollution data
        pollution_data = self._fetch_air_pollution(location.latitude, location.longitude)
        
        # Fetch weather data
        weather_data = self._fetch_weather(location.latitude, location.longitude)

        # Combine into observation
        return self._create_observation(pollution_data, weather_data, location)

    def fetch_historical(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[Observation]:
        """Fetch historical data (requires paid OpenWeather plan)."""
        logger.warning(
            "OpenWeather historical data requires paid plan",
            location=location.location_id
        )
        
        # Fallback to current
        try:
            current = self.fetch_current(location)
            return [current]
        except Exception as e:
            logger.error("Failed to fetch OpenWeather data", error=str(e))
            return []

    def fetch_forecast(self, location: Location, horizon_days: int = 3) -> List[Observation]:
        """Fetch forecast from OpenWeather."""
        is_valid, errors = self.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid OpenWeather configuration: {', '.join(errors)}")

        url = f"{self.BASE_URL}/forecast"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = self.session.get(url, params=params, timeout=settings.request_timeout)
            response.raise_for_status()
            data = response.json()

            forecasts = self._parse_forecast(data, location)
            return forecasts[:horizon_days * 8]  # 8 forecasts per day (3-hour intervals)

        except requests.exceptions.Timeout:
            logger.error("OpenWeather forecast timeout", location=location.location_id)
            raise TimeoutError(f"OpenWeather forecast timeout for {location.location_id}")
        
        except requests.exceptions.RequestException as e:
            logger.error("OpenWeather forecast failed", error=str(e))
            raise ValueError(f"OpenWeather forecast failed: {str(e)}")

    def _fetch_air_pollution(self, lat: float, lon: float) -> dict:
        """Fetch air pollution data."""
        url = f"{self.AIR_POLLUTION_URL}/current"
        params = {"lat": lat, "lon": lon, "appid": self.api_key}

        response = self.session.get(url, params=params, timeout=settings.request_timeout)
        response.raise_for_status()
        return response.json()

    def _fetch_weather(self, lat: float, lon: float) -> dict:
        """Fetch weather data."""
        url = f"{self.BASE_URL}/weather"
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}

        response = self.session.get(url, params=params, timeout=settings.request_timeout)
        response.raise_for_status()
        return response.json()

    def _create_observation(
        self, pollution_data: dict, weather_data: dict, location: Location
    ) -> Observation:
        """Create observation from pollution and weather data."""
        now = datetime.now(timezone.utc)

        # Extract air quality components
        components = pollution_data["list"][0]["components"]
        aqi = pollution_data["list"][0]["main"]["aqi"]
        
        # Convert European AQI (1-5) to US AQI (0-500) approximation
        aqi_conversion = {1: 25, 2: 75, 3: 125, 4: 175, 5: 275}
        aqi_us = aqi_conversion.get(aqi, 100)

        # Extract pollutants (in μg/m³)
        pm25 = components.get("pm2_5")
        pm10 = components.get("pm10")
        o3 = components.get("o3")
        no2 = components.get("no2")
        so2 = components.get("so2")
        co = components.get("co") / 1000 if components.get("co") else None  # Convert to mg/m³

        # Extract weather
        temperature = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]
        pressure = weather_data["main"]["pressure"]
        wind_speed = weather_data["wind"]["speed"]
        wind_direction = weather_data["wind"].get("deg")
        clouds = weather_data["clouds"]["all"]
        
        # Precipitation (3h accumulation)
        precipitation = 0.0
        if "rain" in weather_data and "3h" in weather_data["rain"]:
            precipitation = weather_data["rain"]["3h"] / 3.0  # Convert to hourly

        # Create payload hash
        payload_str = str(pollution_data) + str(weather_data)
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()

        # Count missing fields
        fields = [pm25, pm10, o3, no2, so2, co, temperature, humidity]
        missing_count = sum(1 for f in fields if f is None)

        observation = Observation(
            location_id=location.location_id,
            city=location.city,
            country=location.country,
            latitude=location.latitude,
            longitude=location.longitude,
            source="openweather",
            observed_at=datetime.fromtimestamp(weather_data["dt"], tz=timezone.utc),
            retrieved_at=now,
            timezone=location.timezone,
            aqi=float(aqi_us),
            pm25=pm25,
            pm10=pm10,
            o3=o3,
            no2=no2,
            so2=so2,
            co=co,
            temperature_c=temperature,
            humidity_pct=humidity,
            pressure_hpa=pressure,
            wind_speed_ms=wind_speed,
            wind_direction_deg=wind_direction,
            precipitation_mm=precipitation,
            cloud_pct=clouds,
            is_observed=True,
            is_forecast=False,
            missing_field_count=missing_count,
            data_quality_flag="good" if missing_count < 2 else "fair",
            raw_payload_hash=payload_hash,
        )

        return observation

    def _parse_forecast(self, data: dict, location: Location) -> List[Observation]:
        """Parse forecast data into observations."""
        observations = []

        for item in data.get("list", []):
            obs_time = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            
            # Create simplified forecast observation (weather only, no pollutants)
            obs = Observation(
                location_id=location.location_id,
                city=location.city,
                country=location.country,
                latitude=location.latitude,
                longitude=location.longitude,
                source="openweather",
                observed_at=obs_time,
                retrieved_at=datetime.now(timezone.utc),
                timezone=location.timezone,
                aqi=None,
                pm25=None,
                pm10=None,
                o3=None,
                no2=None,
                so2=None,
                co=None,
                temperature_c=item["main"]["temp"],
                humidity_pct=item["main"]["humidity"],
                pressure_hpa=item["main"]["pressure"],
                wind_speed_ms=item["wind"]["speed"],
                wind_direction_deg=item["wind"].get("deg"),
                precipitation_mm=item.get("rain", {}).get("3h", 0) / 3.0,
                cloud_pct=item["clouds"]["all"],
                is_observed=False,
                is_forecast=True,
                missing_field_count=6,  # No pollutant data
                data_quality_flag="fair",
                raw_payload_hash=None,
            )
            observations.append(obs)

        return observations

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openweather"

    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate OpenWeather configuration."""
        errors = []

        if not self.api_key:
            errors.append("OpenWeather API key is required")

        return len(errors) == 0, errors
