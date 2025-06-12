from pathlib import Path
from typing import List, Optional, Dict
import logging
import requests
from docker.models.containers import Container
from .docker_manager import DockerManager, ContainerNotFoundError
from .instance_record_manager import InstanceRecordManager, InstanceRecord

logger = logging.getLogger("foundry-manager")

class FoundryInstance:
    """Represents a Foundry VTT instance."""
    
    def __init__(self, name: str, version: str, data_dir: Path, port: int, container=None):
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
        if self._container:
            return self._container.status
        return "unknown"

class FoundryInstanceManager:
    """Manages Foundry VTT instances."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.docker_manager = DockerManager(self.base_dir)
        self.record_manager = InstanceRecordManager(self.base_dir)
    
    def create_instance(self, name: str, version: Optional[str] = None, port: int = 30000, environment: Dict[str, str] = None) -> FoundryInstance:
        """Create a new Foundry VTT instance."""
        container = None
        data_dir = self.base_dir / name
        
        try:
            # Check if container already exists
            try:
                existing_container = self.docker_manager.get_container(name)
                if existing_container:
                    # Remove existing container
                    logger.info(f"Removing existing container {name}")
                    self.docker_manager.remove_container(name)
            except ContainerNotFoundError:
                pass  # Container doesn't exist, which is what we want
            
            # Get available versions if version not specified
            if not version:
                versions = self.get_available_versions()
                if not versions:
                    raise ValueError("No Foundry VTT versions available")
                version = versions[0]['version']  # Use the first available version
            
            # Create data directory
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine if SSL is enabled and get proxy port
            proxy_port = None
            if environment and environment.get('FOUNDRY_PROXY_SSL', '').lower() == 'true':
                proxy_port = int(environment.get('FOUNDRY_PROXY_PORT', '443'))
            
            # Create container
            container = self.docker_manager.create_container(
                name=name,
                image=f"felddy/foundryvtt:{version}",
                volumes={str(data_dir): {'bind': '/data', 'mode': 'rw'}},
                environment=environment or {},
                port=port,
                proxy_port=proxy_port
            )
            
            # Create instance
            instance = FoundryInstance(
                name=name,
                version=version,
                data_dir=data_dir,
                port=port,
                container=container
            )
            
            # Add record
            self.record_manager.add_record(InstanceRecord(
                name=name,
                version=version,
                data_dir=data_dir,
                port=port,
                status="created"
            ))
            
            return instance
            
        except Exception as e:
            # Clean up on error
            if container:
                try:
                    self.docker_manager.remove_container(name)
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up container after error: {cleanup_error}")
            
            # Remove data directory if it was created
            if data_dir.exists():
                try:
                    for item in data_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            item.rmdir()
                    data_dir.rmdir()
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up data directory after error: {cleanup_error}")
            
            # Re-raise the original error
            raise
    
    def get_instance(self, name: str) -> Optional[FoundryInstance]:
        """Get a Foundry instance by name."""
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
            container=container
        )
    
    def list_instances(self) -> List[FoundryInstance]:
        """List all Foundry instances."""
        instances = []
        for record in self.record_manager.get_all_records():
            container = self.docker_manager.get_container(record.name)
            instances.append(FoundryInstance(
                name=record.name,
                version=record.version,
                data_dir=record.data_dir,
                port=record.port,
                container=container
            ))
        return instances
    
    def start_instance(self, name: str) -> None:
        """Start a Foundry instance."""
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")
        
        self.docker_manager.start_container(name)
        self.record_manager.update_status(name, "running")
    
    def stop_instance(self, name: str) -> None:
        """Stop a Foundry instance."""
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")
        
        self.docker_manager.stop_container(name)
        self.record_manager.update_status(name, "stopped")
    
    def remove_instance(self, name: str) -> None:
        """Remove a Foundry instance and its data."""
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")
        
        # Stop and remove container if it exists
        try:
            if instance.status == "running":
                self.stop_instance(name)
            self.docker_manager.remove_container(name)
        except ContainerNotFoundError:
            # Container is already gone, which is fine
            logger.info(f"Container {name} not found during removal, proceeding with cleanup")
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            raise
        
        # Remove data directory recursively
        if instance.data_dir.exists():
            def remove_directory(path):
                for item in path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        remove_directory(item)
                path.rmdir()
            
            try:
                remove_directory(instance.data_dir)
            except Exception as e:
                logger.error(f"Failed to remove data directory: {e}")
                raise
        
        # Remove record
        self.record_manager.remove_record(name)
    
    def migrate_instance(self, name: str, version: str) -> None:
        """Migrate a Foundry instance to a new version."""
        instance = self.get_instance(name)
        if not instance:
            raise ValueError(f"Instance {name} not found")
        
        # Stop instance if running
        was_running = instance.status == "running"
        if was_running:
            self.stop_instance(name)
        
        # Remove old container
        self.docker_manager.remove_container(name)
        
        # Create new container with same configuration
        container = self.docker_manager.create_container(
            name=name,
            image=f"felddy/foundryvtt:{version}",
            volumes={str(instance.data_dir): {'bind': '/data', 'mode': 'rw'}},
            environment={},  # TODO: Preserve environment variables
            port=instance.port
        )
        
        # Update record
        self.record_manager.update_version(name, version)
        
        # Start instance if it was running
        if was_running:
            self.start_instance(name)
    
    def get_available_versions(self) -> List[Dict[str, str]]:
        """Get a list of available Foundry VTT versions from Docker Hub."""
        try:
            # Get tags from Docker Hub API
            response = requests.get("https://registry.hub.docker.com/v2/repositories/felddy/foundryvtt/tags")
            response.raise_for_status()
            
            # Filter and sort versions
            versions = []
            for tag in response.json()['results']:
                # Skip 'latest' and non-version tags
                if tag['name'] == 'latest' or not tag['name'].replace('.', '').isdigit():
                    continue
                    
                versions.append({
                    'version': tag['name'],
                    'last_updated': tag['last_updated']
                })
            
            # Sort by version number
            versions.sort(key=lambda x: [int(n) for n in x['version'].split('.')], reverse=True)
            return versions
        except (requests.RequestException, Exception) as e:
            logger.error(f"Failed to get available versions: {e}")
            return []
    
    def create_instances_from_config(self, config: Optional[dict] = None) -> List[FoundryInstance]:
        """Create instances based on the configuration.
        
        Args:
            config: Optional configuration dictionary. If not provided, loads from default config file.
        """
        if config is None:
            from .config import get_instances
            instance_configs = get_instances()
        else:
            instance_configs = config.get('instances', {})
        
        created_instances = []
        
        # Get all existing instances
        existing_instances = self.list_instances()
        existing_names = {instance.name for instance in existing_instances}
        config_names = set(instance_configs.keys())
        
        # Remove instances that are not in the config
        instances_to_remove = existing_names - config_names
        for name in instances_to_remove:
            try:
                logger.info(f"Removing instance {name} as it's not in the config")
                self.remove_instance(name)
            except Exception as e:
                logger.error(f"Failed to remove instance {name}: {e}")
                # Continue with other instances even if one fails
                continue
        
        # Create or update instances from config
        for name, instance_config in instance_configs.items():
            try:
                # Check if instance exists
                existing_instance = self.get_instance(name)
                if existing_instance:
                    # Check if instance needs to be updated
                    needs_update = (
                        existing_instance.version != instance_config['version'] or
                        existing_instance.port != instance_config['port'] or
                        existing_instance.data_dir != Path(instance_config['data_dir'])
                    )
                    
                    if needs_update:
                        logger.info(f"Updating instance {name} to match config")
                        # Remove existing instance
                        self.remove_instance(name)
                        # Create new instance
                        instance = self.create_instance(
                            name=name,
                            version=instance_config['version'],
                            port=instance_config['port'],
                            environment=instance_config.get('environment', {})
                        )
                        created_instances.append(instance)
                    else:
                        logger.info(f"Instance {name} already matches config, skipping")
                        created_instances.append(existing_instance)
                    continue
                
                # Create new instance
                instance = self.create_instance(
                    name=name,
                    version=instance_config['version'],
                    port=instance_config['port'],
                    environment=instance_config.get('environment', {})
                )
                created_instances.append(instance)
                logger.info(f"Created instance {name} from config")
                
            except Exception as e:
                logger.error(f"Failed to create/update instance {name} from config: {e}")
                # Continue with other instances even if one fails
                continue
        
        return created_instances
