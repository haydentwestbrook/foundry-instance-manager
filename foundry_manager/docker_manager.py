#!/usr/bin/env python3

import docker
import requests
from rich.console import Console
from rich.table import Table
from pathlib import Path
from typing import Optional, List, Dict

console = Console()

class DockerManager:
    FOUNDRY_IMAGE = "felddy/foundryvtt"
    
    def __init__(self, base_dir: Path = None):
        self.client = docker.from_env()
        self.base_dir = base_dir or Path.cwd()
        self.shared_data_dir = self.base_dir / "data" / "shared"
        self.containers_data_dir = self.base_dir / "data" / "containers"
        
        # Create necessary directories if they don't exist
        self.shared_data_dir.mkdir(parents=True, exist_ok=True)
        self.containers_data_dir.mkdir(parents=True, exist_ok=True)

    def get_available_versions(self) -> List[Dict[str, str]]:
        """Get list of available Foundry VTT versions from Docker Hub."""
        try:
            # Get tags from Docker Hub API
            response = requests.get(f"https://registry.hub.docker.com/v2/repositories/{self.FOUNDRY_IMAGE}/tags")
            response.raise_for_status()
            
            # Filter and sort versions
            versions = []
            for tag in response.json()['results']:
                if tag['name'] != 'latest':
                    versions.append({
                        'version': tag['name'],
                        'last_updated': tag['last_updated']
                    })
            
            # Sort by version number
            versions.sort(key=lambda x: x['version'], reverse=True)
            return versions
        except requests.RequestException as e:
            console.print(f"[red]Error fetching versions: {str(e)}[/red]")
            return []

    def create_container(self, name: str, image: str = None, version: str = None):
        """Create a new container with individual and shared data directories."""
        container_data_dir = self.containers_data_dir / name
        container_data_dir.mkdir(exist_ok=True)

        # Construct image name with version if specified
        if version:
            image = f"{self.FOUNDRY_IMAGE}:{version}"
        elif not image:
            image = f"{self.FOUNDRY_IMAGE}:latest"

        try:
            container = self.client.containers.create(
                image=image,
                name=name,
                volumes={
                    str(container_data_dir): {'bind': '/data/container', 'mode': 'rw'},
                    str(self.shared_data_dir): {'bind': '/data/shared', 'mode': 'ro'}
                },
                detach=True
            )
            console.print(f"[green]Successfully created container: {name} with image {image}[/green]")
            return container
        except docker.errors.ImageNotFound:
            console.print(f"[red]Error: Image {image} not found[/red]")
            raise
        except docker.errors.APIError as e:
            console.print(f"[red]Error creating container: {str(e)}[/red]")
            raise

    def list_containers(self):
        """List all containers managed by this tool."""
        containers = self.client.containers.list(all=True)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Image")
        table.add_column("Version")

        for container in containers:
            image_tags = container.image.tags[0] if container.image.tags else "N/A"
            version = image_tags.split(':')[-1] if ':' in image_tags else "latest"
            table.add_row(
                container.name,
                container.status,
                image_tags,
                version
            )
        
        console.print(table)

    def migrate_container(self, name: str, new_version: str):
        """Migrate a container to a new Foundry VTT version."""
        try:
            # Get current container
            container = self.client.containers.get(name)
            current_image = container.image.tags[0] if container.image.tags else "N/A"
            
            # Stop the container
            if container.status == "running":
                container.stop()
            
            # Remove the container but keep the data
            container.remove()
            
            # Create new container with the same name and data
            new_image = f"{self.FOUNDRY_IMAGE}:{new_version}"
            self.create_container(name, image=new_image)
            
            console.print(f"[green]Successfully migrated {name} from {current_image} to {new_image}[/green]")
        except docker.errors.NotFound:
            console.print(f"[red]Error: Container {name} not found[/red]")
            raise
        except docker.errors.APIError as e:
            console.print(f"[red]Error during migration: {str(e)}[/red]")
            raise

    def start_container(self, name: str):
        """Start a container by name."""
        try:
            container = self.client.containers.get(name)
            container.start()
            console.print(f"[green]Successfully started container: {name}[/green]")
        except docker.errors.NotFound:
            console.print(f"[red]Error: Container {name} not found[/red]")
            raise
        except docker.errors.APIError as e:
            console.print(f"[red]Error starting container: {str(e)}[/red]")
            raise

    def stop_container(self, name: str):
        """Stop a container by name."""
        try:
            container = self.client.containers.get(name)
            container.stop()
            console.print(f"[green]Successfully stopped container: {name}[/green]")
        except docker.errors.NotFound:
            console.print(f"[red]Error: Container {name} not found[/red]")
            raise
        except docker.errors.APIError as e:
            console.print(f"[red]Error stopping container: {str(e)}[/red]")
            raise

    def remove_container(self, name: str):
        """Remove a container by name."""
        try:
            container = self.client.containers.get(name)
            container.remove(force=True)
            # Remove container's data directory
            container_data_dir = self.containers_data_dir / name
            if container_data_dir.exists():
                for item in container_data_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        for subitem in item.iterdir():
                            subitem.unlink()
                container_data_dir.rmdir()
            console.print(f"[green]Successfully removed container: {name}[/green]")
        except docker.errors.NotFound:
            console.print(f"[red]Error: Container {name} not found[/red]")
            raise
        except docker.errors.APIError as e:
            console.print(f"[red]Error removing container: {str(e)}[/red]")
            raise 