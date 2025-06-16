"""Foundry VTT instance manager module.

This module provides functionality for managing Foundry VTT instances using Docker.
"""

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker

from foundry_manager.config import get_base_dir

from .game_system_manager import GameSystemManager
from .module_manager import ModuleManager
from .world_manager import WorldManager

logger = logging.getLogger(__name__)


@dataclass
class FoundryInstance:
    """Represents a Foundry VTT instance."""

    name: str
    version: str
    port: int
    data_dir: Path
    status: str
    container: Optional[docker.models.containers.Container] = None
    admin_key: Optional[str] = None
    environment: Optional[Dict[str, str]] = None

    def is_running(self) -> bool:
        """Check if the instance is running."""
        return self.status == "running"

    def to_dict(self) -> Dict:
        """Convert instance to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "port": self.port,
            "data_dir": str(self.data_dir),
            "status": self.status,
            "admin_key": self.admin_key,
            "environment": self.environment,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FoundryInstance":
        """Create instance from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            port=data["port"],
            data_dir=Path(data["data_dir"]),
            status=data["status"],
            admin_key=data.get("admin_key"),
            environment=data.get("environment"),
        )


class FoundryInstanceManager:
    """Manages Foundry VTT instances using Docker."""

    def __init__(self, base_dir: Optional[Path] = None, docker_client=None):
        """Initialize the Foundry VTT instance manager.

        Args:
            base_dir: Base directory for instance data. If not provided,
                     uses the default from config.
            docker_client: Optional Docker client for testing/mocking.
        """
        self.base_dir = Path(base_dir) if base_dir is not None else get_base_dir()
        self.docker = docker_client or docker.from_env()
        self.client = self.docker  # For backward compatibility
        self.instances_dir = self.base_dir / "instances"
        self.instances_dir.mkdir(parents=True, exist_ok=True)

    def _check_docker(self) -> None:
        """Check if Docker is available and running.

        Raises:
            RuntimeError: If Docker is not available or not running.
        """
        if self.client is None:
            raise RuntimeError("Docker is not available")
        try:
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"Docker is not running: {e}")

    def _get_instance_path(self, instance_name: str) -> Path:
        """Get the path for an instance's data directory.

        Args:
            instance_name: Name of the instance.

        Returns:
            Path to the instance's data directory.
        """
        return self.instances_dir / instance_name

    def _get_instance_config_path(self, instance_name: str) -> Path:
        """Get the path for an instance's configuration file.

        Args:
            instance_name: Name of the instance.

        Returns:
            Path to the instance's configuration file.
        """
        return self._get_instance_path(instance_name) / "config.json"

    def _load_instance_config(self, instance_name: str) -> Dict:
        """Load an instance's configuration.

        Args:
            instance_name: Name of the instance.

        Returns:
            Dictionary containing the instance's configuration.

        Raises:
            FileNotFoundError: If the instance configuration file doesn't exist.
        """
        config_path = self._get_instance_config_path(instance_name)
        if not config_path.exists():
            raise FileNotFoundError(f"Instance {instance_name} not found")
        with open(config_path) as f:
            return json.load(f)

    def _save_instance_config(self, instance_name: str, config: Dict) -> None:
        """Save an instance's configuration.

        Args:
            instance_name: Name of the instance.
            config: Configuration to save.
        """
        config_path = self._get_instance_config_path(instance_name)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def _get_instance_paths(self) -> List[Path]:
        """Get paths to all instance directories.

        Returns:
            List of paths to instance directories.
        """
        return [p for p in self.instances_dir.iterdir() if p.is_dir()]

    def create_instance(
        self,
        name: str,
        version: str,
        port: int,
        admin_key: str,
        username: str,
        password: str,
    ) -> None:
        """Create a new Foundry VTT instance.

        Args:
            name: Name for the new instance.
            version: Foundry VTT version to use.
            port: Port to run the instance on.
            admin_key: Admin key for the instance.
            username: Foundry VTT username.
            password: Foundry VTT password.

        Raises:
            ValueError: If an instance with the given name already exists.
            RuntimeError: If the instance fails to be created.
        """
        instance_path = None
        try:
            # Check if instance already exists
            if self._get_instance_config_path(name).exists():
                raise ValueError(f"Instance {name} already exists")

            # Create instance directory
            instance_path = self._get_instance_path(name)
            instance_path.mkdir(parents=True, exist_ok=True)

            # Create Docker container
            container = self.docker.containers.run(
                f"felddy/foundryvtt:{version}",
                name=f"foundry-{name}",
                detach=True,
                ports={f"{port}/tcp": port},
                volumes={str(instance_path): {"bind": "/data", "mode": "rw"}},
                environment={
                    "FOUNDRY_USERNAME": username,
                    "FOUNDRY_PASSWORD": password,
                    "FOUNDRY_ADMIN_KEY": admin_key,
                },
            )

            # Save instance configuration
            config = {
                "name": name,
                "version": version,
                "port": port,
                "data_dir": str(instance_path),
                "status": "created",
                "admin_key": admin_key,
                "username": username,
                "password": password,
            }
            self._save_instance_config(name, config)

        except Exception as e:
            # Clean up on failure
            if instance_path and instance_path.exists():
                shutil.rmtree(instance_path)
            try:
                container = self.docker.containers.get(f"foundry-{name}")
                container.remove(force=True)
            except docker.errors.NotFound:
                # Container doesn't exist, which is fine
                pass
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Failed to create instance {name}: {str(e)}")

    def start_instance(self, name: str) -> None:
        """Start a Foundry VTT instance.

        Args:
            name: Name of the instance to start.

        Raises:
            ValueError: If the instance doesn't exist.
            RuntimeError: If the instance fails to start.
        """
        try:
            config = self._load_instance_config(name)
            try:
                container = self.docker.containers.get(f"foundry-{name}")
                container.start()
                config["status"] = "running"
                self._save_instance_config(name, config)
            except docker.errors.NotFound:
                raise ValueError(f"Instance {name} not found")
        except FileNotFoundError:
            raise ValueError(f"Instance {name} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to start instance {name}: {str(e)}")

    def stop_instance(self, name: str) -> None:
        """Stop a Foundry VTT instance.

        Args:
            name: Name of the instance to stop.

        Raises:
            ValueError: If the instance doesn't exist.
            RuntimeError: If the instance fails to stop.
        """
        try:
            config = self._load_instance_config(name)
            try:
                container = self.docker.containers.get(f"foundry-{name}")
                container.stop()
                config["status"] = "stopped"
                self._save_instance_config(name, config)
            except docker.errors.NotFound:
                raise ValueError(f"Instance {name} not found")
        except FileNotFoundError:
            raise ValueError(f"Instance {name} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to stop instance {name}: {str(e)}")

    def remove_instance(self, name: str) -> None:
        """Remove a Foundry VTT instance.

        Args:
            name: Name of the instance to remove.

        Raises:
            ValueError: If the instance doesn't exist.
            RuntimeError: If the instance fails to be removed.
        """
        try:
            self._load_instance_config(name)
            try:
                container = self.docker.containers.get(f"foundry-{name}")
                container.remove(force=True)
                instance_path = self._get_instance_path(name)
                if instance_path.exists():
                    shutil.rmtree(instance_path)
            except docker.errors.NotFound:
                raise ValueError(f"Instance {name} not found")
        except FileNotFoundError:
            raise ValueError(f"Instance {name} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to remove instance {name}: {str(e)}")

    def list_instances(self) -> List[Dict[str, Any]]:
        """List all Foundry VTT instances.

        Returns:
            List of instance dictionaries.
        """
        instances = []
        for path in self._get_instance_paths():
            try:
                config = self._load_instance_config(path.name)
                instances.append(config)
            except Exception as e:
                logger.error(f"Failed to load instance {path.name}: {e}")
        return instances

    def get_instance_status(self, name: str) -> str:
        """Get the status of a Foundry VTT instance.

        Args:
            name: Name of the instance.

        Returns:
            Status of the instance.

        Raises:
            FileNotFoundError: If the instance doesn't exist.
            RuntimeError: If Docker is not available.
        """
        self._check_docker()
        self._load_instance_config(name)

        try:
            container = self.docker.containers.get(f"foundry-{name}")
            return container.status
        except Exception:
            return "not_found"
        except Exception as e:
            raise RuntimeError(f"Failed to get instance status: {e}")

    def get_available_versions(self) -> List[str]:
        """Get available Foundry VTT versions.

        Returns:
            List of available versions.

        Raises:
            RuntimeError: If Docker is not available.
        """
        self._check_docker()
        try:
            image = self.docker.images.get("felddy/foundryvtt")
            return [tag.split(":")[1] for tag in image.tags]
        except Exception as e:
            raise RuntimeError(f"Failed to get available versions: {e}")

    def migrate_instance(self, name: str, version: str) -> None:
        """Migrate a Foundry VTT instance to a new version."""
        try:
            config = self._load_instance_config(name)
            container = self.docker.containers.get(f"foundry-{name}")

            # Stop the container
            container.stop()

            # Remove the container
            container.remove()

            # Create new container with updated version
            self.create_instance(
                name=name,
                version=version,
                port=config["port"],
                admin_key=config["admin_key"],
                username=config["username"],
                password=config["password"],
            )

            # Update config
            config["version"] = version
            self._save_instance_config(name, config)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise ValueError(f"Instance {name} not found")
            raise RuntimeError(f"Failed to migrate instance: {str(e)}")

    def get_instance_path(self, instance_name: str) -> Optional[Path]:
        """Get the path for an instance's data directory.

        Args:
            instance_name: Name of the instance.

        Returns:
            Path to the instance's data directory, or None if the instance doesn't exist.
        """
        path = self._get_instance_path(instance_name)
        return path if path.exists() else None

    def list_systems(self, instance_name: str) -> List[Dict[str, Any]]:
        """List all game systems for an instance.

        Args:
            instance_name: Name of the instance.

        Returns:
            List of system dictionaries.

        Raises:
            ValueError: If the instance doesn't exist.
        """
        instance_path = self.get_instance_path(instance_name)
        if not instance_path:
            raise ValueError(f"Instance {instance_name} not found")
        system_manager = GameSystemManager(instance_path)
        return system_manager.list_systems()

    def list_modules(self, instance_name: str) -> List[Dict[str, Any]]:
        """List all modules for an instance.

        Args:
            instance_name: Name of the instance.

        Returns:
            List of module dictionaries.

        Raises:
            ValueError: If the instance doesn't exist.
        """
        instance_path = self.get_instance_path(instance_name)
        if not instance_path:
            raise ValueError(f"Instance {instance_name} not found")
        module_manager = ModuleManager(self.docker, instance_name, instance_path)
        return module_manager.list_modules()

    def list_worlds(self, instance_name: str) -> List[Dict[str, Any]]:
        """List all worlds for an instance.

        Args:
            instance_name: Name of the instance.

        Returns:
            List of world dictionaries.

        Raises:
            ValueError: If the instance doesn't exist.
        """
        instance_path = self.get_instance_path(instance_name)
        if not instance_path:
            raise ValueError(f"Instance {instance_name} not found")
        world_manager = WorldManager(instance_path)
        return world_manager.list_worlds()

    def create_instances_from_config(
        self, config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create or update instances based on configuration.

        Args:
            config: Configuration dictionary containing instance definitions.

        Returns:
            List of created/updated instance dictionaries.
        """
        instances = []
        for name, instance_config in config.get("instances", {}).items():
            try:
                # Check if instance exists
                existing_config = None
                try:
                    existing_config = self._load_instance_config(name)
                except FileNotFoundError:
                    pass

                # Create or update instance
                if existing_config:
                    # Update existing instance
                    self.migrate_instance(name, instance_config["version"])
                    if "admin_key" in instance_config:
                        self._save_instance_config(name, instance_config)
                else:
                    # Create new instance
                    self.create_instance(
                        name=name,
                        version=instance_config["version"],
                        port=instance_config["port"],
                        admin_key=instance_config.get("admin_key", ""),
                        username=instance_config.get("username", ""),
                        password=instance_config.get("password", ""),
                    )

                instances.append(self._load_instance_config(name))
            except Exception as e:
                logger.error(f"Failed to create/update instance {name}: {e}")
                raise

        return instances

    def apply_config(self, config: Dict[str, Any]) -> None:
        """Apply configuration to instances.

        Args:
            config: Configuration dictionary containing instance definitions.
        """
        self.create_instances_from_config(config)
        existing_instances = self.list_instances()
        existing_names = {instance["name"] for instance in existing_instances}
        config_names = set(config.get("instances", {}).keys())

        # Remove instances not in config
        for name in existing_names - config_names:
            try:
                self.remove_instance(name)
            except Exception as e:
                logger.error(f"Failed to remove instance {name}: {e}")
                raise
