"""Game System Management Module.

This module provides functionality for managing game systems in Foundry VTT instances.
It handles installing, removing, and listing game systems for each instance.
"""

import json
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("foundry-manager")


class GameSystemManager:
    """Manages game systems for Foundry VTT instances."""

    def __init__(self, instance_data_dir: Path):
        """Initialize the GameSystemManager with an instance's data directory.

        Args:
            instance_data_dir: Path to the instance's data directory
        """
        self.instance_data_dir = instance_data_dir
        self.systems_dir = instance_data_dir / "Data" / "systems"

    def list_systems(self, instance=None) -> List[Dict[str, str]]:
        """List all installed game systems.

        Args:
            instance: Optional FoundryInstance object (not used, kept for API compatibility)

        Returns:
            List of dictionaries containing system information
        """
        if not self.systems_dir.exists():
            return []

        systems = []
        for system_dir in self.systems_dir.iterdir():
            if not system_dir.is_dir():
                continue

            system_json = system_dir / "system.json"
            if not system_json.exists():
                continue

            try:
                with open(system_json) as f:
                    system_data = json.load(f)
                    system_id = system_data.get("id", system_dir.name)
                    system_title = system_data.get("title", "Unknown")
                    system_version = system_data.get("version", "Unknown")
                    system_path = str(system_dir)
                    systems.append(
                        {
                            "id": system_id,
                            "title": system_title,
                            "version": system_version,
                            "path": system_path,
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to read system.json for {system_dir}: {e}")
                continue

        return systems

    def _download_system(self, system_url: str, temp_path: Path) -> Path:
        """Download a game system from a URL.

        Args:
            system_url: URL to download the system from
            temp_path: Path to save the downloaded file

        Returns:
            Path to the downloaded zip file

        Raises:
            ValueError: If download fails
        """
        try:
            response = requests.get(system_url, stream=True)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(f"Failed to download system: {e}")

        zip_path = temp_path / "system.zip"
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return zip_path

    def _extract_system(self, zip_path: Path, temp_path: Path) -> Path:
        """Extract a downloaded system archive.

        Args:
            zip_path: Path to the zip file
            temp_path: Path to extract to

        Returns:
            Path to the extracted system directory

        Raises:
            ValueError: If extraction fails or no system.json is found
        """
        try:
            with zipfile.ZipFile(zip_path) as zip_ref:
                zip_ref.extractall(temp_path)
        except zipfile.BadZipFile:
            raise ValueError("Invalid system archive")

        # Find the system.json file
        for root, _, files in os.walk(temp_path):
            if "system.json" in files:
                return Path(root)

        raise ValueError("No system.json found in archive")

    def _read_system_info(self, system_json: Path) -> Dict:
        """Read system information from system.json.

        Args:
            system_json: Path to system.json

        Returns:
            Dictionary containing system information

        Raises:
            ValueError: If system.json is invalid or missing required fields
        """
        try:
            with open(system_json) as f:
                system_data = json.load(f)
        except json.JSONDecodeError:
            raise ValueError("Invalid system.json file")

        system_id = system_data.get("id")
        if not system_id:
            raise ValueError("No system ID found in system.json")

        return system_data

    def _move_system_files(
        self, extracted_dir: Path, system_dir: Path, system_json: Path
    ) -> None:  # noqa: E501
        """Move system files to the systems directory.

        Args:
            extracted_dir: Path to the extracted system directory
            system_dir: Path to the target system directory
            system_json: Path to the system.json file
        """
        system_dir.mkdir(parents=True, exist_ok=True)

        # Move all files from the extracted directory to the system directory
        for item in extracted_dir.iterdir():
            if item.name != "system.json":  # Skip system.json as we'll copy it last
                if item.is_file():
                    shutil.copy2(item, system_dir)
                elif item.is_dir():
                    shutil.copytree(item, system_dir / item.name)

        # Copy system.json last to ensure it's the most recent file
        shutil.copy2(system_json, system_dir / "system.json")

    def install_system(self, instance=None, system_url: Optional[str] = None) -> None:
        """Install a game system from a URL.

        Args:
            instance: Optional FoundryInstance object (not used, kept for API compatibility)
            system_url: URL to the game system's manifest or repository

        Raises:
            ValueError: If the system URL is invalid or installation fails
        """
        if not system_url:
            raise ValueError("system_url is required")

        # Create systems directory if it doesn't exist
        self.systems_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download the system
            zip_path = self._download_system(system_url, temp_path)

            # Extract the system
            extracted_dir = self._extract_system(zip_path, temp_path)
            system_json = extracted_dir / "system.json"

            # Read system information
            system_data = self._read_system_info(system_json)
            system_id = system_data["id"]

            # Check if system is already installed (flake8 E501 fix)
            system_path = self.systems_dir / system_id
            if system_path.exists():
                raise ValueError("System {} is already installed".format(system_id))

            # Move the system files
            system_dir = self.systems_dir / system_id
            self._move_system_files(extracted_dir, system_dir, system_json)

            version = system_data.get("version", "unknown")
            logger.info(f"Installed system {system_id} version " f"{version}")

    def remove_system(self, instance=None, system_id: Optional[str] = None) -> None:
        """Remove a game system.

        Args:
            instance: Optional FoundryInstance object (not used, kept for API compatibility)
            system_id: ID of the system to remove

        Raises:
            ValueError: If the system is not found
        """
        if not system_id:
            raise ValueError("system_id is required")

        system_dir = self.systems_dir / system_id
        if not system_dir.exists():
            raise ValueError(f"System {system_id} not found")

        try:
            # Remove the system directory
            for item in system_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            system_dir.rmdir()
        except Exception as e:
            logger.error(f"Failed to remove system {system_id}: {e}")
            raise ValueError(f"Failed to remove system {system_id}: {e}")

    def get_system_info(self, system_id: str) -> Optional[Dict[str, str]]:
        """Get information about a specific game system.

        Args:
            system_id: ID of the system to get information for

        Returns:
            Dictionary containing system information, or None if not found
        """
        system_dir = self.systems_dir / system_id
        if not system_dir.exists():
            return None

        system_json = system_dir / "system.json"
        if not system_json.exists():
            return None

        try:
            with open(system_json) as f:
                system_data = json.load(f)
                return {
                    "id": system_data.get("id", system_id),
                    "title": system_data.get("title", "Unknown"),
                    "version": system_data.get("version", "Unknown"),
                    "path": str(system_dir),
                }
        except Exception as e:
            logger.error(f"Failed to read system.json for {system_id}: {e}")
            return None
