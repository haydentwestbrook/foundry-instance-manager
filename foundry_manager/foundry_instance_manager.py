"""Core functionality for managing Foundry VTT instances and their Docker containers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from docker.models.containers import Container

from .docker_manager import ContainerNotFoundError, DockerManager
from .instance_record_manager import InstanceRecord, InstanceRecordManager

logger = logging.getLogger("foundry-manager")


class FoundryInstance:
    """Represents a Foundry VTT instance."""

    def __init__(
        self, name: str, version: str, data_dir: Path, port: int, container=None
    ):
        """Initialize a Foundry VTT instance.

        Args:
            name: The name of the instance
            version: The Foundry VTT version
            data_dir: The directory where instance data will be stored
            port: The port the instance will run on
            container: Optional Docker container associated with this instance
        """
        self.name = name
        self.version = version
        self.data_dir = data_dir
        self.port = port
        self._container = container

    @property
    def container(self) -> Optional[Container]:
        """Get the container associated with this instance."""
        return self._container

    @container.setter
    def container(self, value):
        """Set the container associated with this instance."""
        self._container = value

    @property
    def status(self) -> str:
        """Get the current status of the instance."""
        if not self._container:
            return "unknown"

        container_status = self._container.status
        if container_status == "running":
            # Check if container is healthy
            health = self._container.attrs.get("State", {}).get("Health", {})
            if health and health.get("Status") == "starting":
                return "starting"
            return "running"
        return container_status


class FoundryInstanceManager:
    """Manages Foundry VTT instances."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the Foundry instance manager.

        Args:
            base_dir: Optional base directory for instance data.
            Defaults to current directory.
        """
        self.base_dir = base_dir or Path.cwd()
        self.docker_manager = DockerManager(self.base_dir)
        self.record_manager = InstanceRecordManager(self.base_dir)

    def _cleanup_existing_container(self, name: str) -> None:
        """Clean up any existing container with the given name.

        Args:
            name: Name of the container to clean up
        """
        try:
            existing_container = self.docker_manager.get_container(name)
            if existing_container:
                logger.info(f"Removing existing container {name}")
                self.docker_manager.remove_container(name)
        except ContainerNotFoundError:
            pass  # Container doesn't exist, which is what we want

    def _get_version(self, version: Optional[str] = None) -> str:
        """Get the Foundry VTT version to use.

        Args:
            version: Optional specific version to use

        Returns:
            Version string to use

        Raises:
            ValueError: If no versions are available
        """
        if version:
            return version

        versions = self.get_available_versions()
        if not versions:
            raise ValueError("No Foundry VTT versions available")
        return versions[0]["version"]  # Use the first available version

    def _setup_data_directory(self, data_dir: Path) -> None:
        """Set up the data directory for an instance.

        Args:
            data_dir: Path to the data directory
        """
        data_dir.mkdir(parents=True, exist_ok=True)

    def _get_proxy_port(
        self, environment: Optional[Dict[str, str]] = None
    ) -> Optional[int]:  # noqa: E501
        """Get the proxy port from environment variables if SSL is enabled.

        Args:
            environment: Optional environment variables dictionary

        Returns:
            Proxy port if SSL is enabled, None otherwise
        """
        if environment and environment.get("FOUNDRY_PROXY_SSL", "").lower() == "true":
            return int(environment.get("FOUNDRY_PROXY_PORT", "443"))
        return None

    def _cleanup_on_error(
        self, name: str, data_dir: Path, container: Optional[Container] = None
    ) -> None:  # noqa: E501
        """Clean up resources if instance creation fails.

        Args:
            name: Name of the instance
            data_dir: Path to the data directory
            container: Optional container to clean up
        """
        if container:
            try:
                self.docker_manager.remove_container(name)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to clean up container after error: {cleanup_error}"
                )  # noqa: E501

        if data_dir.exists():
            try:
                for item in data_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        item.rmdir()
                data_dir.rmdir()
            except Exception:
                logger.error("Failed to clean up data directory after error")

    def create_instance(
        self,
        name: str,
        version: Optional[str] = None,
        port: int = 30000,
        environment: Optional[Dict[str, str]] = None,
    ) -> FoundryInstance:
        """Create a new Foundry VTT instance.

        Args:
            name: Name of the instance
            version: Foundry VTT version to use. If None, uses latest available version.
            port: Port to expose the instance on
            environment: Optional environment variables for the container

        Returns:
            Created FoundryInstance object

        Raises:
            ValueError: If no versions are available or instance creation fails
        """
        container = None
        data_dir = self.base_dir / name
        shared_assets_dir = self.base_dir / "shared_assets"

        try:
            # Clean up any existing container
            self._cleanup_existing_container(name)

            # Get version to use
            version = self._get_version(version)

            # Set up data directory
            self._setup_data_directory(data_dir)

            # Get proxy port if SSL is enabled
            proxy_port = self._get_proxy_port(environment)

            # Set up volumes
            volumes = {
                str(data_dir): {"bind": "/data", "mode": "rw"},
                str(shared_assets_dir): {"bind": "/data/shared_assets", "mode": "ro"},
            }

            # Create container
            container = self.docker_manager.create_container(
                name=name,
                image=f"felddy/foundryvtt:{version}",
                volumes=volumes,
                environment=environment or {},
                port=port,
                proxy_port=proxy_port,
            )

            # Create instance
            instance = FoundryInstance(
                name=name,
                version=version,
                data_dir=data_dir,
                port=port,
                container=container,
            )

            # Save instance record
            self.record_manager.add_record(
                InstanceRecord(
                    name=name,
                    version=version,
                    data_dir=data_dir,
                    port=port,
                    status="created",
                )
            )

            return instance
        except Exception as e:
            self._cleanup_on_error(name, data_dir, container)
            raise ValueError(f"Failed to create instance: {str(e)}")

    def get_instance(self, name: str) -> Optional[FoundryInstance]:
        """Get a Foundry instance by name.

        Args:
            name: Name of the instance to get

        Returns:
            FoundryInstance object if found, None otherwise
        """
        # Get record
        record = self.record_manager.get_record(name)
        if not record:
            return None

        # Get container
        container = self.docker_manager.get_container(name)

        return FoundryInstance(
            name=name,
            version=record.version,
            data_dir=record.data_dir,
            port=record.port,
            container=container,
        )

    def list_instances(self) -> List[FoundryInstance]:
        """List all Foundry instances.

        Returns:
            List of FoundryInstance objects
        """
        instances = []
        for record in self.record_manager.get_all_records():
            container = self.docker_manager.get_container(record.name)
            instances.append(
                FoundryInstance(
                    name=record.name,
                    version=record.version,
                    data_dir=record.data_dir,
                    port=record.port,
                    container=container,
                )
            )
        return instances

    def start_instance(self, name: str) -> None:
        """Start a Foundry instance.

        Args:
            name: Name of the instance to start

        Raises:
            ValueError: If instance is not found
        """
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")

        self.docker_manager.start_container(name)
        self.record_manager.update_status(name, "running")

    def stop_instance(self, name: str) -> None:
        """Stop a Foundry instance.

        Args:
            name: Name of the instance to stop

        Raises:
            ValueError: If instance is not found
        """
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")

        self.docker_manager.stop_container(name)
        self.record_manager.update_status(name, "stopped")

    def _cleanup_container(self, name: str) -> None:
        """Clean up a container by stopping and removing it.

        Args:
            name: Name of the container to clean up
        """
        try:
            self.docker_manager.stop_container(name)
        except ContainerNotFoundError:
            pass

        try:
            self.docker_manager.remove_container(name)
        except ContainerNotFoundError:
            pass

    def _remove_data_directory(self, path: Path) -> None:
        """Remove a data directory and all its contents.

        Args:
            path: Path to the directory to remove

        Raises:
            Exception: If directory removal fails
        """
        if not path.exists():
            return

        def remove_directory(dir_path: Path) -> None:
            for item in dir_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    remove_directory(item)
            dir_path.rmdir()

        try:
            remove_directory(path)
        except Exception:
            logger.error("Failed to remove data directory")
            raise

    def remove_instance(self, name: str) -> None:
        """Remove a Foundry instance and its data.

        Args:
            name: Name of the instance to remove

        Raises:
            ValueError: If instance is not found
        """
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")

        # Clean up container
        self._cleanup_container(name)

        # Remove data directory
        self._remove_data_directory(instance.data_dir)

        # Remove record
        self.record_manager.remove_record(name)

    def migrate_instance(self, name: str, version: str) -> None:
        """Migrate a Foundry instance to a new version.

        Args:
            name: Name of the instance to migrate
            version: New version to migrate to

        Raises:
            ValueError: If instance is not found
        """
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")

        # Stop instance
        try:
            self.docker_manager.stop_container(name)
        except ContainerNotFoundError:
            pass

        # Remove container
        try:
            self.docker_manager.remove_container(name)
        except ContainerNotFoundError:
            pass

        # Get proxy port if SSL is enabled
        proxy_port = self._get_proxy_port(
            instance.container.attrs["Config"]["Env"] if instance.container else {}
        )

        # Create new container with new version
        self.docker_manager.create_container(
            name=name,
            image=f"felddy/foundryvtt:{version}",
            volumes={str(instance.data_dir): {"bind": "/data", "mode": "rw"}},
            environment=(
                instance.container.attrs["Config"]["Env"] if instance.container else {}
            ),
            port=instance.port,
            proxy_port=proxy_port,
        )

        # Update record
        self.record_manager.update_version(name, version)

        # Start the container if it was running before
        if instance.status == "running":
            self.docker_manager.start_container(name)
            self.record_manager.update_status(name, "running")

    def get_available_versions(self) -> List[Dict[str, str]]:
        """Get available Foundry VTT versions.

        Returns:
            List of dictionaries containing version information
        """
        return self.docker_manager.get_available_versions()

    def create_instances_from_config(
        self, config: Optional[Dict] = None
    ) -> List["FoundryInstance"]:
        """Create instances from a configuration dictionary.

        Args:
            config: Optional configuration dictionary. If not provided, loads from
                   default config file.

        Returns:
            List of created FoundryInstance objects.
        """
        if config is None:
            from .config import load_config

            config = load_config()

        instances = []
        for name, instance_config in config.get("instances", {}).items():
            try:
                instance = self.create_instance(
                    name=name,
                    version=instance_config.get("version"),
                    port=instance_config.get("port", 30000),
                    environment=instance_config.get("environment", {}),
                )
                instances.append(instance)
            except Exception as e:
                logger.error(f"Failed to create instance {name}: {e}")
                raise

        return instances

    def get_instance_path(self, name: str) -> Optional[Path]:
        """Get the path to an instance's data directory.

        Args:
            name: The name of the instance.

        Returns:
            Path to the instance's data directory, or None if the instance doesn't exist.
        """
        instance_path = self.base_dir / name
        if not instance_path.exists():
            return None
        return instance_path
