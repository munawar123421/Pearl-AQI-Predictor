"""Feature store abstraction and implementation."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from pearls_aqi.logging_config import get_logger
from pearls_aqi.settings import settings

logger = get_logger(__name__)


class FeatureStore(ABC):
    """Abstract base class for feature store implementations."""

    @abstractmethod
    def write_observations(self, df: pd.DataFrame):
        """Write raw observations to the feature store."""
        pass

    @abstractmethod
    def write_features(self, df: pd.DataFrame):
        """Write engineered features to the feature store."""
        pass

    @abstractmethod
    def read_features(
        self,
        location_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Read features from the feature store."""
        pass

    @abstractmethod
    def read_training_dataset(
        self, location_id: Optional[str] = None, min_rows: int = 168
    ) -> pd.DataFrame:
        """Read complete training dataset with features and targets."""
        pass

    @abstractmethod
    def get_latest_features(self, location_id: str) -> Optional[pd.Series]:
        """Get the latest feature vector for a location."""
        pass

    @abstractmethod
    def write_metadata(self, metadata: Dict[str, Any]):
        """Write feature store metadata."""
        pass

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get feature store health status."""
        pass


class LocalFeatureStore(FeatureStore):
    """Local filesystem-based feature store using Parquet."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize local feature store.
        
        Args:
            base_path: Base directory for feature store (uses settings if None)
        """
        self.base_path = base_path or settings.feature_store_absolute_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.observations_path = self.base_path / "observations"
        self.features_path = self.base_path / "features"
        self.metadata_path = self.base_path / "metadata"
        
        for path in [self.observations_path, self.features_path, self.metadata_path]:
            path.mkdir(parents=True, exist_ok=True)

    def write_observations(self, df: pd.DataFrame):
        """Write raw observations to disk."""
        if df.empty:
            logger.warning("No observations to write")
            return

        location_id = df["location_id"].iloc[0]
        
        # Partition by location and date
        df["date"] = pd.to_datetime(df["observed_at"]).dt.date
        
        for date, group in df.groupby("date"):
            date_str = date.isoformat()
            partition_path = self.observations_path / location_id / date_str
            partition_path.mkdir(parents=True, exist_ok=True)
            
            filepath = partition_path / "observations.parquet"
            
            # Append if exists, otherwise create new
            if filepath.exists():
                existing_df = pd.read_parquet(filepath)
                combined_df = pd.concat([existing_df, group], ignore_index=True)
                combined_df = combined_df.drop_duplicates(
                    subset=["location_id", "observed_at"], keep="last"
                )
                combined_df.to_parquet(filepath, compression="snappy", index=False)
            else:
                group.to_parquet(filepath, compression="snappy", index=False)
        
        logger.info(
            "Wrote observations",
            location=location_id,
            rows=len(df),
            dates=df["date"].nunique(),
        )

    def write_features(self, df: pd.DataFrame):
        """Write engineered features to disk."""
        if df.empty:
            logger.warning("No features to write")
            return

        location_id = df["location_id"].iloc[0]
        
        # Partition by location and date
        df["date"] = pd.to_datetime(df["observed_at"]).dt.date
        
        for date, group in df.groupby("date"):
            date_str = date.isoformat()
            partition_path = self.features_path / location_id / date_str
            partition_path.mkdir(parents=True, exist_ok=True)
            
            filepath = partition_path / "features.parquet"
            
            # Append if exists, otherwise create new
            if filepath.exists():
                existing_df = pd.read_parquet(filepath)
                combined_df = pd.concat([existing_df, group], ignore_index=True)
                combined_df = combined_df.drop_duplicates(
                    subset=["location_id", "observed_at"], keep="last"
                )
                combined_df.to_parquet(filepath, compression="snappy", index=False)
            else:
                group.to_parquet(filepath, compression="snappy", index=False)
        
        logger.info(
            "Wrote features",
            location=location_id,
            rows=len(df),
            features=len(df.columns),
        )

    def read_features(
        self,
        location_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Read features from disk."""
        all_dfs = []
        
        # Determine which locations to read
        if location_id:
            locations = [location_id]
        else:
            locations = [d.name for d in self.features_path.iterdir() if d.is_dir()]
        
        for loc in locations:
            loc_path = self.features_path / loc
            if not loc_path.exists():
                continue
            
            # Read all date partitions
            for date_dir in loc_path.iterdir():
                if not date_dir.is_dir():
                    continue
                
                filepath = date_dir / "features.parquet"
                if not filepath.exists():
                    continue
                
                try:
                    df = pd.read_parquet(filepath)
                    all_dfs.append(df)
                except Exception as e:
                    logger.warning("Failed to read features", filepath=str(filepath), error=str(e))
        
        if not all_dfs:
            return pd.DataFrame()
        
        # Combine all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # Apply time filters
        if start_time or end_time:
            combined_df["observed_at"] = pd.to_datetime(combined_df["observed_at"])
            if start_time:
                combined_df = combined_df[combined_df["observed_at"] >= start_time]
            if end_time:
                combined_df = combined_df[combined_df["observed_at"] <= end_time]
        
        combined_df = combined_df.sort_values("observed_at").reset_index(drop=True)
        
        logger.info(
            "Read features",
            locations=len(locations),
            rows=len(combined_df),
        )
        
        return combined_df

    def read_training_dataset(
        self, location_id: Optional[str] = None, min_rows: int = 168
    ) -> pd.DataFrame:
        """Read complete training dataset."""
        df = self.read_features(location_id=location_id)
        
        if len(df) < min_rows:
            logger.warning(
                "Insufficient data for training",
                rows=len(df),
                min_required=min_rows,
            )
        
        return df

    def get_latest_features(self, location_id: str) -> Optional[pd.Series]:
        """Get the latest feature vector."""
        df = self.read_features(location_id=location_id)
        
        if df.empty:
            return None
        
        df["observed_at"] = pd.to_datetime(df["observed_at"])
        latest = df.sort_values("observed_at").iloc[-1]
        
        return latest

    def write_metadata(self, metadata: Dict[str, Any]):
        """Write metadata to disk."""
        import json
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.metadata_path / f"metadata_{timestamp}.json"
        
        with open(filepath, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info("Wrote metadata", filepath=str(filepath))

    def get_health_status(self) -> Dict[str, Any]:
        """Get feature store health status."""
        # Count locations and total rows
        locations = [d.name for d in self.features_path.iterdir() if d.is_dir()]
        
        total_rows = 0
        latest_time = None
        
        for loc in locations:
            try:
                df = self.read_features(location_id=loc)
                total_rows += len(df)
                
                if not df.empty:
                    df["observed_at"] = pd.to_datetime(df["observed_at"])
                    loc_latest = df["observed_at"].max()
                    if latest_time is None or loc_latest > latest_time:
                        latest_time = loc_latest
            except Exception as e:
                logger.warning("Error reading location", location=loc, error=str(e))
        
        # Calculate freshness
        hours_since_latest = None
        is_stale = False
        
        if latest_time:
            hours_since_latest = (datetime.now() - latest_time.replace(tzinfo=None)).total_seconds() / 3600
            is_stale = hours_since_latest > 6
        
        status = {
            "locations": len(locations),
            "total_rows": total_rows,
            "latest_observation": latest_time.isoformat() if latest_time else None,
            "hours_since_latest": round(hours_since_latest, 2) if hours_since_latest else None,
            "is_stale": is_stale,
            "storage_path": str(self.base_path),
        }
        
        return status


def get_feature_store(backend: Optional[str] = None) -> FeatureStore:
    """Get configured feature store instance.
    
    Args:
        backend: Feature store backend ('local', 'hopsworks', 'vertex_ai')
                 Uses settings if None
        
    Returns:
        Feature store instance
    """
    backend = backend or settings.feature_store_backend
    
    if backend == "local":
        return LocalFeatureStore()
    else:
        raise NotImplementedError(f"Feature store backend '{backend}' not implemented")
