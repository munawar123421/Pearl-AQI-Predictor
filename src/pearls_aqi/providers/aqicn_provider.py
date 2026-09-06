"""AQICN data provider implementation."""

import hashlib
import time
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


class AQICNProvider(DataProvider):
    """AQICN (World Air Quality Index) data provider."""

    BASE_URL = "https://api.waqi.info"

    def __init__(self, token: Optional[str] = None):
        """Initialize AQICN provider.
        
        Args:
            token: AQICN API token (from settings if not provided)
        """
        self.token = token or settings.aqicn_token
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
        """Fetch current air quality data from AQICN."""
        is_valid, errors = self.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid AQICN configuration: {', '.join(errors)}")

        station = location.aqicn_station or settings.aqicn_station
        
        url = f"{self.BASE_URL}/feed/{station}/"
        params = {"token": self.token}

        try:
            response = self.session.get(
                url, params=params, timeout=settings.request_timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                raise ValueError(f"AQICN API error: {data.get('data', 'Unknown error')}")

            return self._parse_observation(data["data"], location)

        except requests.exceptions.Timeout:
            logger.error("AQICN request timeout", location=location.location_id)
            raise TimeoutError(f"AQICN request timeout for {location.location_id}")
        
        except requests.exceptions.RequestException as e:
            logger.error("AQICN request failed", error=str(e), location=location.location_id)
            raise ValueError(f"AQICN request failed: {str(e)}")

    def fetch_historical(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[Observation]:
        """Fetch historical data (not fully supported by AQICN free tier).
        
        Note: AQICN free tier has limited historical data access.
        This method returns available recent observations.
        """
        logger.warning(
            "AQICN historical data limited",
            location=location.location_id,
            message="Free tier has limited historical access"
        )
        
        # Fetch current as best effort
        try:
            current = self.fetch_current(location)
            return [current]
        except Exception as e:
            logger.error("Failed to fetch AQICN historical data", error=str(e))
            return []

    def fetch_forecast(self, location: Location, horizon_days: int = 3) -> List[Observation]:
        """Fetch forecast data from AQICN."""
        is_valid, errors = self.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid AQICN configuration: {', '.join(errors)}")

        station = location.aqicn_station or settings.aqicn_station
        
        url = f"{self.BASE_URL}/feed/{station}/"
        params = {"token": self.token}

        try:
            response = self.session.get(
                url, params=params, timeout=settings.request_timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                raise ValueError(f"AQICN API error: {data.get('data', 'Unknown error')}")

            # AQICN provides forecast in the response
            forecasts = []
            if "forecast" in data.get("data", {}):
                forecast_data = data["data"]["forecast"]
                forecasts = self._parse_forecast(forecast_data, location)

            return forecasts

        except requests.exceptions.Timeout:
            logger.error("AQICN forecast timeout", location=location.location_id)
            raise TimeoutError(f"AQICN forecast timeout for {location.location_id}")
        
        except requests.exceptions.RequestException as e:
            logger.error("AQICN forecast failed", error=str(e), location=location.location_id)
            raise ValueError(f"AQICN forecast failed: {str(e)}")

    def _parse_observation(self, data: dict, location: Location) -> Observation:
        """Parse AQICN response into Observation."""
        now = datetime.now(timezone.utc)
        
        # Parse observation time
        time_data = data.get("time", {})
        obs_time_str = time_data.get("iso")
        if obs_time_str:
            obs_time = datetime.fromisoformat(obs_time_str.replace("Z", "+00:00"))
        else:
            obs_time = now

        # Extract AQI
        aqi = data.get("aqi")
        if isinstance(aqi, str):
            aqi = float(aqi) if aqi != "-" else None

        # Extract pollutants
        iaqi = data.get("iaqi", {})
        
        def get_pollutant(name: str) -> Optional[float]:
            val = iaqi.get(name, {}).get("v")
            return float(val) if val is not None else None

        pm25 = get_pollutant("pm25")
        pm10 = get_pollutant("pm10")
        o3 = get_pollutant("o3")
        no2 = get_pollutant("no2")
        so2 = get_pollutant("so2")
        co = get_pollutant("co")

        # Extract weather
        temperature = get_pollutant("t")
        humidity = get_pollutant("h")
        pressure = get_pollutant("p")
        wind_speed = get_pollutant("w")

        # Create payload hash
        payload_str = str(data)
        payload_hash = hashlib.md5(payload_str.encode()).hexdigest()

        # Count missing fields
        fields = [pm25, pm10, o3, no2, so2, co, temperature, humidity, pressure]
        missing_count = sum(1 for f in fields if f is None)

        observation = Observation(
            location_id=location.location_id,
            city=location.city,
            country=location.country,
            latitude=location.latitude,
            longitude=location.longitude,
            source="aqicn",
            observed_at=obs_time,
            retrieved_at=now,
            timezone=location.timezone,
            aqi=aqi,
            pm25=pm25,
            pm10=pm10,
            o3=o3,
            no2=no2,
            so2=so2,
            co=co,
            temperature_c=temperature,
            humidity_pct=humidity,
            pressure_hpa=pressure,
            wind_speed_ms=wind_speed / 3.6 if wind_speed else None,  # Convert km/h to m/s
            wind_direction_deg=None,
            precipitation_mm=None,
            cloud_pct=None,
            is_observed=True,
            is_forecast=False,
            missing_field_count=missing_count,
            data_quality_flag="good" if missing_count < 3 else "fair",
            raw_payload_hash=payload_hash,
        )

        return observation

    def _parse_forecast(self, forecast_data: dict, location: Location) -> List[Observation]:
        """Parse AQICN forecast data."""
        observations = []
        
        # AQICN provides daily forecasts
        daily_forecasts = forecast_data.get("daily", {})
        
        for pollutant, values in daily_forecasts.items():
            # Process forecast values (simplified)
            pass
        
        # Return empty list if parsing not fully implemented
        return observations

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "aqicn"

    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate AQICN configuration."""
        errors = []

        if not self.token:
            errors.append("AQICN token is required")

        return len(errors) == 0, errors
