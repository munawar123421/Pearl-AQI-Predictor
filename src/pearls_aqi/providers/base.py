"""Base interface for data providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from pearls_aqi.schemas import Location, Observation


class DataProvider(ABC):
    """Abstract base class for data providers."""

    @abstractmethod
    def fetch_current(self, location: Location) -> Observation:
        """Fetch current observation for a location.
        
        Args:
            location: Location configuration
            
        Returns:
            Current observation
            
        Raises:
            ValueError: If data cannot be fetched
            TimeoutError: If request times out
        """
        pass

    @abstractmethod
    def fetch_historical(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[Observation]:
        """Fetch historical observations for a time range.
        
        Args:
            location: Location configuration
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            
        Returns:
            List of historical observations
            
        Raises:
            ValueError: If data cannot be fetched
            TimeoutError: If request times out
        """
        pass

    @abstractmethod
    def fetch_forecast(self, location: Location, horizon_days: int = 3) -> List[Observation]:
        """Fetch forecast observations.
        
        Args:
            location: Location configuration
            horizon_days: Number of days to forecast
            
        Returns:
            List of forecast observations
            
        Raises:
            ValueError: If data cannot be fetched
            TimeoutError: If request times out
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate provider configuration.
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        pass
