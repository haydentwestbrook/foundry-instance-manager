#!/usr/bin/env python3

import docker
from rich.console import Console
from rich.table import Table
from pathlib import Path
from typing import Optional, List, Dict
import shutil
import logging
from docker.models.containers import Container

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
        except docker.errors.NotFound:
            logger.error(f"Container not found: {name}")
            raise ContainerNotFoundError(f"Container '{name}' not found")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while getting container {name}: {e}")
            raise DockerError(f"Failed to get container: {str(e)}")

    def create_container(self, name: str, image: str, environment: Optional[Dict[str, str]] = None, 
                        port: Optional[int] = None, volumes: Optional[Dict[str, Dict]] = None,
                        proxy_port: Optional[int] = None) -> Container:
        """Create a new Docker container."""
        try:
            # Set up port mappings
            ports = {
                '30000/tcp': ('127.0.0.1', port if port is not None else 30000)
            }
            
            # Add proxy port if specified
            if proxy_port is not None:
                ports['443/tcp'] = ('127.0.0.1', proxy_port)

            # Create container with environment variables
            container = self.client.containers.run(
                image=image,
                name=name,
                detach=True,
                ports=ports,
                volumes=volumes or {},
                environment=environment or {},
                restart_policy={'Name': 'unless-stopped'}
            )
            logger.info(f"Container {name} created successfully")
            return container

        except docker.errors.ImageNotFound:
            logger.error(f"Docker image not found: {image}")
            raise DockerError(f"Image '{image}' not found")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while creating container: {e}")
            raise DockerError(f"Failed to create container: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while creating container: {e}")
            raise DockerError(f"Failed to create container: {str(e)}")

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
            container.remove(v=True, force=True)
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