#!/usr/bin/env python3

"""Docker container management for Foundry VTT instances."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import docker
from docker.models.containers import Container
from rich.console import Console

console = Console()
logger = logging.getLogger("foundry-manager")


class DockerError(Exception):
    """Base exception for Docker-related errors."""

    pass


class ContainerNotFoundError(DockerError):
    """Raised when a container is not found."""

    pass


class ContainerOperationError(DockerError):
    """Raised when a container operation fails."""

    pass


class DockerManager:
    """Manages Docker containers for Foundry VTT instances."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the Docker manager."""
        self.base_dir = base_dir or Path.cwd()
        self.containers_data_dir = self.base_dir / "containers"
        self.shared_data_dir = self.base_dir / "shared"

        # Create necessary directories
        self.containers_data_dir.mkdir(parents=True, exist_ok=True)
        self.shared_data_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.client = docker.from_env()
            logger.debug("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            logger.error("Failed to initialize Docker client")
            raise DockerError("Docker is not running or not accessible") from e

    def get_container(self, name: str) -> Container:
        """Get a container by name, raising appropriate exceptions if not found."""
        try:
            container = self.client.containers.get(name)
            logger.debug(f"Found container: {name}")
            return container
        except (docker.errors.NotFound, Exception) as e:
            logger.debug(f"Container not found: {name}", e)
            raise ContainerNotFoundError(f"Container '{name}' not found")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while getting container {name}: {e}")
            raise DockerError(f"Failed to get container: {str(e)}")

    def create_container(
        self,
        name: str,
        image: str,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        environment: Optional[Dict[str, str]] = None,
        port: int = 30000,
        proxy_port: Optional[int] = None,
    ) -> Container:
        """Create a new container.

        Args:
            name: The name of the container
            image: The Docker image to use
            volumes: Optional volume mappings
            environment: Optional environment variables
            port: The host port to map to container port 30000 (default: 30000)
            proxy_port: Optional proxy port to map

        Returns:
            The created container

        Raises:
            Exception: If container creation fails
        """
        try:
            # Configure ports - always map to container port 30000
            ports = {"30000/tcp": port}
            if proxy_port:
                ports["443/tcp"] = proxy_port

            # Configure health check
            healthcheck = {
                "test": ["CMD", "curl", "-f", "http://localhost:30000/"],
                "interval": 1000000000,  # 1 second in nanoseconds
                "timeout": 3000000000,  # 3 seconds in nanoseconds
                "retries": 3,
                "start_period": 30000000000,  # 30 seconds in nanoseconds
            }

            # Create container with environment variables
            container = self.client.containers.run(  # type: ignore[call-overload]
                image=image,
                name=name,
                detach=True,
                ports=ports,
                volumes=volumes or {},
                environment=environment or {},
                restart_policy={"Name": "unless-stopped"},
                healthcheck=healthcheck,
            )
            return container
        except Exception as e:
            raise Exception(f"Failed to create container: {str(e)}")

    def get_containers(self) -> List[Container]:
        """List all containers."""
        return self.client.containers.list(all=True)

    def start_container(self, name: str) -> None:
        """Start a container."""
        try:
            container = self.get_container(name)
            container.start()
            logger.info(f"Container {name} started successfully")
        except docker.errors.APIError as e:
            logger.error(f"Failed to start container {name}: {e}")
            raise ContainerOperationError(f"Failed to start container: {str(e)}")

    def stop_container(self, name: str) -> None:
        """Stop a container."""
        try:
            container = self.get_container(name)
            container.stop()
            logger.info(f"Container {name} stopped successfully")
        except docker.errors.APIError as e:
            logger.error(f"Failed to stop container {name}: {e}")
            raise ContainerOperationError(f"Failed to stop container: {str(e)}")

    def remove_container(self, name: str) -> None:
        """Remove a container."""
        try:
            container = self.get_container(name)
            container.remove(force=True)
            logger.info(f"Container {name} removed successfully")
        except docker.errors.APIError as e:
            logger.error(f"Failed to remove container {name}: {e}")
            raise ContainerOperationError(f"Failed to remove container: {str(e)}")

    def exec_command(self, name: str, command: str) -> tuple:
        """Execute a command in a container."""
        try:
            container = self.get_container(name)
            return container.exec_run(command)
        except docker.errors.APIError as e:
            logger.error(f"Failed to execute command in container {name}: {e}")
            raise ContainerOperationError(f"Failed to execute command: {str(e)}")

    def get_available_versions(self) -> List[Dict[str, str]]:
        """Get available Foundry VTT versions."""
        try:
            # Get all tags for the felddy/foundryvtt image
            image = self.client.images.get("felddy/foundryvtt")
            versions = []
            for tag in image.tags:
                if ":" in tag:
                    version = tag.split(":")[1]
                    versions.append({"version": version})
            return versions
        except docker.errors.ImageNotFound:
            logger.error("Foundry VTT image not found")
            return []
        except docker.errors.APIError as e:
            logger.error(f"Failed to get available versions: {e}")
            raise DockerError(f"Failed to get available versions: {str(e)}")

    def migrate_container(self, name: str, new_version: str) -> Container:
        """Migrate a container to a new version.

        Args:
            name: The name of the container to migrate
            new_version: The new version to migrate to

        Returns:
            The new container

        Raises:
            ContainerOperationError: If migration fails
        """
        try:
            # Get the current container
            container = self.get_container(name)

            # Stop the container
            container.stop()

            # Get the container's configuration
            container_config = container.attrs

            # Extract the host port from the current container's port bindings
            host_port = None
            if "30000/tcp" in container_config["HostConfig"]["PortBindings"]:
                host_port = int(
                    container_config["HostConfig"]["PortBindings"]["30000/tcp"][0][
                        "HostPort"
                    ]
                )

            # Extract proxy port if it exists
            proxy_port = None
            if "443/tcp" in container_config["HostConfig"]["PortBindings"]:
                proxy_port = int(
                    container_config["HostConfig"]["PortBindings"]["443/tcp"][0][
                        "HostPort"
                    ]
                )

            # Create a new container with the new version
            new_container = self.create_container(
                name=name,
                image=f"felddy/foundryvtt:{new_version}",
                environment=container_config["Config"]["Env"],
                port=host_port or 30000,  # Use existing host port or default to 30000
                proxy_port=proxy_port,
                volumes=container_config["HostConfig"]["Binds"],
            )

            # Remove the old container
            container.remove()

            logger.info(f"Container {name} migrated to version {new_version}")
            return new_container

        except docker.errors.APIError as e:
            logger.error(f"Failed to migrate container {name}: {e}")
            raise ContainerOperationError(f"Failed to migrate container: {str(e)}")
