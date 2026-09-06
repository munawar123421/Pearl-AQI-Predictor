"""Model registry for storing and loading trained models."""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pearls_aqi.logging_config import get_logger
from pearls_aqi.schemas import ModelMetadata
from pearls_aqi.settings import settings

logger = get_logger(__name__)


class ModelRegistry:
    """Local filesystem-based model registry."""

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize model registry.
        
        Args:
            registry_path: Path to registry directory (uses settings if None)
        """
        self.registry_path = registry_path or settings.model_registry_absolute_path
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.models_dir = self.registry_path / "models"
        self.metadata_file = self.registry_path / "registry.json"
        
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load registry
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """Load registry from disk."""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {"models": [], "champion": None}

    def _save_registry(self):
        """Save registry to disk."""
        with open(self.metadata_file, "w") as f:
            json.dump(self.registry, f, indent=2, default=str)

    def register_model(
        self,
        model: Any,
        scaler: Any,
        metadata: Dict,
        model_name: str,
        version: Optional[str] = None,
    ) -> str:
        """Register a new model.
        
        Args:
            model: Trained model object
            scaler: Fitted scaler object
            metadata: Model metadata
            model_name: Name of the model
            version: Version string (auto-generated if None)
            
        Returns:
            Model version string
        """
        # Generate version if not provided
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_id = f"{model_name}_{version}"
        model_dir = self.models_dir / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model artifact
        model_path = model_dir / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        
        # Save scaler
        scaler_path = model_dir / "scaler.pkl"
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        
        # Save metadata
        metadata_copy = metadata.copy()
        metadata_copy.update({
            "model_name": model_name,
            "version": version,
            "model_id": model_id,
            "registered_at": datetime.now().isoformat(),
            "model_path": str(model_path),
            "scaler_path": str(scaler_path),
        })
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata_copy, f, indent=2, default=str)
        
        # Update registry
        self.registry["models"].append(metadata_copy)
        self._save_registry()
        
        logger.info(
            "Registered model",
            model_name=model_name,
            version=version,
            path=str(model_dir),
        )
        
        return version

    def load_model(self, version: str = "champion") -> Dict[str, Any]:
        """Load a model by version.
        
        Args:
            version: Model version or 'champion' for best model
            
        Returns:
            Dictionary with model, scaler, and metadata
        """
        if version == "champion":
            champion_id = self.registry.get("champion")
            if not champion_id:
                raise ValueError("No champion model set")
            version = champion_id
        
        # Find model in registry
        model_metadata = None
        for meta in self.registry["models"]:
            if meta.get("model_id") == version or meta.get("version") == version:
                model_metadata = meta
                break
        
        if not model_metadata:
            raise ValueError(f"Model version '{version}' not found in registry")
        
        model_dir = self.models_dir / model_metadata["model_id"]
        
        # Load model
        model_path = model_dir / "model.pkl"
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        
        # Load scaler
        scaler_path = model_dir / "scaler.pkl"
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        
        logger.info("Loaded model", version=version)
        
        return {
            "model": model,
            "scaler": scaler,
            "metadata": model_metadata,
        }

    def set_champion(self, version: str):
        """Set a model as the champion.
        
        Args:
            version: Model version to promote
        """
        # Verify model exists
        found = False
        for meta in self.registry["models"]:
            if meta.get("version") == version or meta.get("model_id") == version:
                self.registry["champion"] = meta.get("model_id")
                found = True
                break
        
        if not found:
            raise ValueError(f"Model version '{version}' not found")
        
        self._save_registry()
        
        logger.info("Set champion model", version=version)

    def list_models(self) -> List[Dict]:
        """List all registered models.
        
        Returns:
            List of model metadata dictionaries
        """
        return self.registry.get("models", [])

    def get_champion_metadata(self) -> Optional[Dict]:
        """Get metadata for the champion model.
        
        Returns:
            Champion model metadata or None
        """
        champion_id = self.registry.get("champion")
        if not champion_id:
            return None
        
        for meta in self.registry["models"]:
            if meta.get("model_id") == champion_id:
                return meta
        
        return None


# Global registry instance
_registry = None


def get_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
