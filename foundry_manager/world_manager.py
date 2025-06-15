#!/usr/bin/env python3
"""Foundry VTT World Manager.

This module provides functionality for managing Foundry VTT worlds within instances.
It allows users to list, create, backup, and restore worlds through a simple interface.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("foundry-manager")


class WorldManager:
    """Manages Foundry VTT worlds within an instance."""

    def __init__(self, instance_path: Path):
        """Initialize the WorldManager.

        Args:
            instance_path: Path to the Foundry VTT instance data directory.
        """
        self.instance_path = instance_path
        self.worlds_path = instance_path / "Data" / "worlds"
        self.worlds_path.mkdir(parents=True, exist_ok=True)

    def list_worlds(self) -> List[Dict]:
        """List all worlds in the instance.

        Returns:
            List of dictionaries containing world information.
        """
        worlds = []
        for world_dir in self.worlds_path.iterdir():
            if not world_dir.is_dir():
                continue

            world_json = world_dir / "world.json"
            if not world_json.exists():
                continue

            try:
                with open(world_json) as f:
                    world_data = json.load(f)
                    worlds.append(
                        {
                            "id": world_dir.name,
                            "name": world_data.get("name", "Unknown"),
                            "system": world_data.get("system", "Unknown"),
                            "core_version": world_data.get("coreVersion", "Unknown"),
                            "system_version": world_data.get(
                                "systemVersion", "Unknown"
                            ),
                            "last_modified": datetime.fromtimestamp(
                                world_dir.stat().st_mtime
                            ).isoformat(),
                        }
                    )
            except Exception as e:
                logger.error(f"Error reading world {world_dir.name}: {e}")
                continue

        return worlds

    def get_world_info(self, world_id: str) -> Optional[Dict]:
        """Get detailed information about a specific world.

        Args:
            world_id: The ID of the world to get information for.

        Returns:
            Dictionary containing world information, or None if world not found.
        """
        world_dir = self.worlds_path / world_id
        if not world_dir.exists():
            return None

        world_json = world_dir / "world.json"
        if not world_json.exists():
            return None

        try:
            with open(world_json) as f:
                world_data = json.load(f)
                return {
                    "id": world_id,
                    "name": world_data.get("name", "Unknown"),
                    "system": world_data.get("system", "Unknown"),
                    "core_version": world_data.get("coreVersion", "Unknown"),
                    "system_version": world_data.get("systemVersion", "Unknown"),
                    "last_modified": datetime.fromtimestamp(
                        world_dir.stat().st_mtime
                    ).isoformat(),
                    "description": world_data.get("description", ""),
                    "author": world_data.get("author", "Unknown"),
                    "website": world_data.get("website", ""),
                    "minimum_core_version": world_data.get(
                        "minimumCoreVersion", "Unknown"
                    ),
                    "compatible_core_version": world_data.get(
                        "compatibleCoreVersion", "Unknown"
                    ),
                }
        except Exception as e:
            logger.error(f"Error reading world {world_id}: {e}")
            return None

    def create_world(
        self, name: str, system: str, description: str = ""
    ) -> Optional[str]:
        """Create a new world.

        Args:
            name: The name of the world.
            system: The game system to use.
            description: Optional description of the world.

        Returns:
            The ID of the created world, or None if creation failed.
        """
        # Generate a unique world ID based on the name
        world_id = name.lower().replace(" ", "-")
        world_dir = self.worlds_path / world_id

        if world_dir.exists():
            logger.error(f"World {world_id} already exists")
            return None

        try:
            # Create world directory
            world_dir.mkdir(parents=True)

            # Create world.json
            world_data = {
                "id": world_id,
                "name": name,
                "system": system,
                "description": description,
                "coreVersion": "0.0.0",  # Will be updated by Foundry
                "systemVersion": "0.0.0",  # Will be updated by Foundry
                "lastModified": datetime.now().isoformat(),
            }

            with open(world_dir / "world.json", "w") as f:
                json.dump(world_data, f, indent=4)

            return world_id
        except Exception as e:
            logger.error(f"Error creating world {name}: {e}")
            if world_dir.exists():
                shutil.rmtree(world_dir)
            return None

    def backup_world(
        self, world_id: str, backup_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Create a backup of a world.

        Args:
            world_id: The ID of the world to backup.
            backup_path: Optional path to store the backup. If not provided,
                        a timestamped backup will be created in the instance's backup directory.

        Returns:
            Path to the backup file, or None if backup failed.
        """
        world_dir = self.worlds_path / world_id
        if not world_dir.exists():
            logger.error(f"World {world_id} not found")
            return None

        if backup_path is None:
            backup_dir = self.instance_path / "backups" / "worlds"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{world_id}_{timestamp}.zip"

        try:
            shutil.make_archive(
                str(backup_path.with_suffix("")), "zip", self.worlds_path, world_id
            )
            return backup_path
        except Exception as e:
            logger.error(f"Error backing up world {world_id}: {e}")
            return None

    def restore_world(self, backup_path: Path) -> Optional[str]:
        """Restore a world from a backup.

        Args:
            backup_path: Path to the backup file.

        Returns:
            The ID of the restored world, or None if restoration failed.
        """
        if not backup_path.exists():
            logger.error(f"Backup file {backup_path} not found")
            return None

        try:
            # Extract the backup
            shutil.unpack_archive(backup_path, self.worlds_path, "zip")

            # Get the world ID from the extracted directory
            world_id = backup_path.stem.split("_")[0]

            # Verify the world was restored correctly
            world_dir = self.worlds_path / world_id
            if not world_dir.exists():
                logger.error(f"Failed to restore world {world_id}")
                return None

            return world_id
        except Exception as e:
            logger.error(f"Error restoring world from {backup_path}: {e}")
            return None

    def remove_world(self, world_id: str) -> bool:
        """Remove a world.

        Args:
            world_id: The ID of the world to remove.

        Returns:
            True if the world was removed successfully, False otherwise.
        """
        world_dir = self.worlds_path / world_id
        if not world_dir.exists():
            logger.error(f"World {world_id} not found")
            return False

        try:
            shutil.rmtree(world_dir)
            return True
        except Exception as e:
            logger.error(f"Error removing world {world_id}: {e}")
            return False
