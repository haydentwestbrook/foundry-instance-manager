#!/usr/bin/env python3
"""Foundry VTT Module Manager.

This module provides functionality for managing Foundry VTT modules within instances.
It handles module installation, removal, and information retrieval.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
from docker import DockerClient

logger = logging.getLogger("foundry-manager")


class ModuleManager:
    """Manages Foundry VTT modules within instances."""

    def __init__(
        self, docker_client: DockerClient, instance_name: str, data_path: Path
    ):
        """Initialize the module manager.

        Args:
            docker_client: Docker client instance
            instance_name: Name of the Foundry instance
            data_path: Path to the instance's data directory
        """
        self.docker_client = docker_client
        self.instance_name = instance_name
        self.data_path = data_path
        self.modules_path = data_path / "Data" / "modules"

    def list_modules(self) -> List[Dict]:
        """List all installed modules in the instance.

        Returns:
            List of module information dictionaries
        """
        try:
            modules: List[Dict] = []
            if not self.modules_path.exists():
                return modules

            for module_dir in self.modules_path.iterdir():
                if not module_dir.is_dir():
                    continue

                module_json = module_dir / "module.json"
                if not module_json.exists():
                    continue

                with open(module_json) as f:
                    module_data = json.load(f)
                    modules.append(module_data)

            return modules
        except Exception as e:
            logger.error(f"Failed to list modules: {e}")
            raise

    def get_module_info(self, module_id: str) -> Optional[Dict]:
        """Get information about a specific module.

        Args:
            module_id: The module's unique identifier

        Returns:
            Module information dictionary or None if not found
        """
        try:
            module_path = self.modules_path / module_id
            if not module_path.exists():
                return None

            module_json = module_path / "module.json"
            if not module_json.exists():
                return None

            with open(module_json) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get module info: {e}")
            raise

    def install_module(self, module_url: str) -> Dict:
        """Install a module from a URL.

        Args:
            module_url: URL to the module's manifest.json or module.json

        Returns:
            Information about the installed module
        """
        try:
            # Download module manifest
            response = requests.get(module_url)
            response.raise_for_status()
            manifest = response.json()

            # Create module directory
            module_id = manifest["id"]
            module_path = self.modules_path / module_id
            module_path.mkdir(parents=True, exist_ok=True)

            # Save manifest
            with open(module_path / "module.json", "w") as f:
                json.dump(manifest, f, indent=4)

            # Download module files
            if "download" in manifest:
                download_url = manifest["download"]
                response = requests.get(download_url)
                response.raise_for_status()

                # Extract module files
                import io
                import zipfile

                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(module_path)

            return manifest
        except Exception as e:
            logger.error(f"Failed to install module: {e}")
            raise

    def remove_module(self, module_id: str) -> None:
        """Remove a module from the instance.

        Args:
            module_id: The module's unique identifier
        """
        try:
            module_path = self.modules_path / module_id
            if not module_path.exists():
                raise ValueError(f"Module {module_id} not found")

            # Remove module directory
            import shutil

            shutil.rmtree(module_path)
        except Exception as e:
            logger.error(f"Failed to remove module: {e}")
            raise
