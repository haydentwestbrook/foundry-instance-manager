#!/usr/bin/env python3
"""
Foundry VTT Asset Manager.

This module provides functionality for managing shared assets across Foundry VTT
instances. It allows users to upload, organize, and manage assets in a shared directory
accessible by all instances.
"""

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from foundry_manager.asset_processor import AssetProcessor

logger = logging.getLogger("foundry-manager")


class AssetManager:
    """Manages shared assets for Foundry VTT instances."""

    def __init__(self, base_dir: Path):
        """Initialize the AssetManager.

        Args:
            base_dir: Base directory for the Foundry VTT instance manager.
        """
        self.base_dir = base_dir
        self.shared_assets_dir = base_dir / "shared_assets"
        self.asset_index_file = self.shared_assets_dir / "asset_index.json"
        self.processor = AssetProcessor(self._load_processor_config())
        self._setup_directories()
        self._load_index()

    def _load_processor_config(self) -> Dict:
        """Load the processor configuration.

        Returns:
            Dictionary containing the processor configuration.
        """
        config_file = self.base_dir / "config" / "asset_processing.yaml"
        if config_file.exists():
            try:
                import yaml

                with open(config_file) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading processor config: {e}")
        return {}

    def _setup_directories(self) -> None:
        """Set up the necessary directory structure for assets."""
        # Create main shared assets directory
        self.shared_assets_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different asset types
        self.asset_types: Dict[str, List[str]] = {
            "images": ["jpg", "jpeg", "png", "webp", "gif"],
            "audio": ["mp3", "ogg", "wav"],
            "video": ["mp4", "webm"],
            "documents": ["pdf", "html", "json"],
            "models": ["glb", "gltf"],
            "other": [],
        }

        for asset_type in self.asset_types:
            (self.shared_assets_dir / asset_type).mkdir(exist_ok=True)

        # Create empty asset index file if it doesn't exist
        if not self.asset_index_file.exists():
            with open(self.asset_index_file, "w") as f:
                json.dump({}, f)

    def _load_index(self) -> None:
        """Load the asset index file."""
        if self.asset_index_file.exists():
            try:
                with open(self.asset_index_file) as f:
                    self.asset_index = json.load(f)
            except Exception as e:
                logger.error(f"Error loading asset index: {e}")
                self.asset_index = {}
        else:
            self.asset_index = {}

    def _save_index(self) -> None:
        """Save the asset index file."""
        try:
            with open(self.asset_index_file, "w") as f:
                json.dump(self.asset_index, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving asset index: {e}")

    def _get_asset_type(self, file_path: Path) -> str:
        """Determine the asset type based on file extension.

        Args:
            file_path: Path to the asset file.

        Returns:
            String representing the asset type.
        """
        ext = file_path.suffix.lower().lstrip(".")
        for asset_type, extensions in self.asset_types.items():
            if ext in extensions:
                return asset_type
        return "other"

    def _generate_asset_id(self, file_path: Path) -> str:
        """Generate a unique asset ID based on file content.

        Args:
            file_path: Path to the asset file.

        Returns:
            Unique asset ID string.
        """
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return f"{file_path.stem}_{file_hash[:8]}"
        except Exception as e:
            logger.error(f"Error generating asset ID: {e}")
            return f"{file_path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def upload_asset(
        self, file_path: Union[str, Path], metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Upload an asset to the shared directory.

        Args:
            file_path: Path to the asset file to upload.
            metadata: Optional metadata for the asset.

        Returns:
            Asset ID if successful, None otherwise.
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            # Generate asset ID and determine type
            asset_id = self._generate_asset_id(file_path)
            asset_type = self._get_asset_type(file_path)

            # Process the asset
            processed_path = self.processor.process_asset(file_path, asset_type)
            if not processed_path:
                logger.error(f"Failed to process asset: {file_path}")
                return None

            # Create destination path
            dest_dir = self.shared_assets_dir / asset_type
            dest_path = dest_dir / f"{asset_id}{processed_path.suffix}"

            # Copy processed file to shared directory
            shutil.copy2(processed_path, dest_path)

            # Update asset index with original and processed info
            self.asset_index[asset_id] = {
                "id": asset_id,
                "name": file_path.name,
                "type": asset_type,
                "path": str(dest_path.relative_to(self.shared_assets_dir)),
                "original_size": file_path.stat().st_size,
                "processed_size": dest_path.stat().st_size,
                "format": processed_path.suffix.lstrip("."),
                "uploaded": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            self._save_index()

            return asset_id
        except Exception as e:
            logger.error(f"Error uploading asset: {e}")
            return None

    def list_assets(self, asset_type: Optional[str] = None) -> List[Dict]:
        """List all assets or assets of a specific type.

        Args:
            asset_type: Optional asset type to filter by.

        Returns:
            List of asset information dictionaries.
        """
        if asset_type is not None and asset_type not in self.asset_types:
            logger.error(f"Invalid asset type: {asset_type}")
            return []

        assets = []
        for _asset_id, asset_info in self.asset_index.items():
            if not asset_type or asset_info["type"] == asset_type:
                assets.append(asset_info)
        return assets

    def get_asset_info(self, asset_id: str) -> Optional[Dict]:
        """Get information about a specific asset.

        Args:
            asset_id: ID of the asset to get information for.

        Returns:
            Asset information dictionary if found, None otherwise.
        """
        return self.asset_index.get(asset_id)

    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the shared directory.

        Args:
            asset_id: ID of the asset to remove.

        Returns:
            True if successful, False otherwise.
        """
        try:
            asset_info = self.asset_index.get(asset_id)
            if not asset_info:
                logger.error(f"Asset not found: {asset_id}")
                return False

            # Remove file
            asset_path = self.shared_assets_dir / asset_info["path"]
            if asset_path.exists():
                asset_path.unlink()

            # Update index
            del self.asset_index[asset_id]
            self._save_index()

            return True
        except Exception as e:
            logger.error(f"Error removing asset: {e}")
            return False

    def get_asset_path(self, asset_id: str) -> Optional[Path]:
        """Get the full path to an asset.

        Args:
            asset_id: ID of the asset to get the path for.

        Returns:
            Full path to the asset if found, None otherwise.
        """
        asset_info = self.asset_index.get(asset_id)
        if not asset_info:
            return None
        return self.shared_assets_dir / asset_info["path"]
