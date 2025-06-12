#!/usr/bin/env python3

import click
import json
from pathlib import Path
import logging
from foundry_manager.foundry_instance_manager import FoundryInstanceManager
from foundry_manager.cli_output import (
    print_instance_table,
    print_versions_table,
    print_success,
    print_error,
    print_info,
    print_warning
)

logger = logging.getLogger("foundry-manager")

# Constants
CONFIG_FILE_NAME = ".fim"

def load_config():
    """Load configuration from file."""
    config_path = Path.home() / CONFIG_FILE_NAME / "config.json"
    if not config_path.exists():
        return {"base_dir": str(Path.home() / CONFIG_FILE_NAME)}
    
    with open(config_path) as f:
        return json.load(f)

def save_config(config):
    """Save configuration to file."""
    config_path = Path.home() / CONFIG_FILE_NAME / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

@click.group()
def cli():
    """Foundry VTT Instance Manager CLI"""
    pass

@cli.command()
@click.option('--base-dir', help='Base directory for container data')
def set_base_dir(base_dir):
    """Set the base directory for Foundry VTT instances."""
    try:
        config = load_config()
        config['base_dir'] = base_dir
        save_config(config)
        print_success("Base directory set successfully")
    except Exception as e:
        logger.error(f"Failed to set base directory: {e}")
        raise click.ClickException("Failed to set base directory")

@cli.command()
@click.option('--username', help='Foundry VTT username')
@click.option('--password', help='Foundry VTT password')
def set_credentials(username, password):
    """Set the Foundry VTT username and password."""
    try:
        config = load_config()
        config['foundry_username'] = username
        config['foundry_password'] = password
        save_config(config)
        print_success("Foundry VTT credentials set successfully")
    except Exception as e:
        logger.error(f"Failed to set credentials: {e}")
        raise click.ClickException("Failed to set credentials")

@cli.command()
@click.argument('name')
@click.option('--version', help='Foundry VTT version')
@click.option('--port', type=int, help='External port to map Foundry VTT to (default: 30000)', default=30000)
@click.option('--environment', multiple=True, help='Environment variables in the format KEY=VALUE')
@click.option('--admin-key', envvar='FOUNDRY_ADMIN_KEY', help='Foundry VTT admin key')
@click.option('--proxy-port', default=443, help='Foundry VTT proxy port')
@click.option('--proxy-ssl/--no-proxy-ssl', default=True, help='Enable SSL proxy')
@click.option('--minify/--no-minify', default=True, help='Minify static files')
@click.option('--update-channel', default='release', type=click.Choice(['release', 'stable', 'development']), help='Update channel')
def create(name, version, port, environment, admin_key, proxy_port, proxy_ssl, minify, update_channel):
    """Create a new Foundry VTT instance."""
    try:
        env_dict = dict(e.split('=', 1) for e in environment)
        config = load_config()
        
        # Validate required credentials
        if not config.get('foundry_username') or not config.get('foundry_password'):
            print_error("Foundry VTT credentials not set")
            raise click.ClickException("Foundry VTT credentials not set. Use 'set-credentials' command first.")

        # Set Foundry-specific environment variables
        env_dict.update({
            'FOUNDRY_USERNAME': config.get('foundry_username', ''),
            'FOUNDRY_PASSWORD': config.get('foundry_password', ''),
            'FOUNDRY_ADMIN_KEY': admin_key,
            'FOUNDRY_PROXY_PORT': str(proxy_port),
            'FOUNDRY_PROXY_SSL': str(proxy_ssl).lower(),
            'FOUNDRY_MINIFY_STATIC_FILES': str(minify).lower(),
            'FOUNDRY_UPDATE_CHANNEL': update_channel,
            'FOUNDRY_DATA_PATH': '/data',
            'FOUNDRY_HOSTNAME': '0.0.0.0',
            'FOUNDRY_PORT': '30000'
        })

        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        
        # Create instance
        instance = manager.create_instance(
            name=name,
            version=version,
            port=port,
            environment=env_dict
        )
        
        print_success(f"Instance {name} created successfully")
        print_info(f"Access Foundry VTT at:")
        print_info(f"HTTP:  http://localhost:{port}")
        if proxy_ssl:
            print_info(f"HTTPS: https://localhost:{proxy_port}")
    except Exception as e:
        logger.error(f"Failed to create instance: {e}")
        raise click.ClickException(f"Failed to create instance: {str(e)}")

@cli.command()
@click.argument('name')
def start(name):
    """Start a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        manager.start_instance(name)
        print_success(f"Instance {name} started successfully")
    except Exception as e:
        logger.error(f"Failed to start instance: {e}")
        raise click.ClickException(f"Failed to start instance: {str(e)}")

@cli.command()
@click.argument('name')
def stop(name):
    """Stop a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        manager.stop_instance(name)
        print_success(f"Instance {name} stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop instance: {e}")
        raise click.ClickException(f"Failed to stop instance: {str(e)}")

@cli.command()
@click.argument('name')
def remove(name):
    """Remove a Foundry VTT instance and its data."""
    if not click.confirm(f"Warning: Removing instance '{name}' will delete all data associated with this Foundry server. Are you sure you want to proceed?", default=False):
        return
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        manager.remove_instance(name)
        print_success(f"Instance {name} removed successfully")
    except Exception as e:
        logger.error(f"Failed to remove instance: {e}")
        raise click.ClickException(f"Failed to remove instance: {str(e)}")

@cli.command()
@click.argument('name')
@click.argument('version')
def migrate(name, version):
    """Migrate a Foundry VTT instance to a new version."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        manager.migrate_instance(name, version)
        print_success(f"Instance {name} migrated to version {version} successfully")
    except Exception as e:
        logger.error(f"Failed to migrate instance: {e}")
        raise click.ClickException(f"Failed to migrate instance: {str(e)}")

@cli.command()
def list():
    """List all Foundry VTT instances and their status."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        instances = manager.list_instances()
        
        # Convert instances to dictionaries for the table formatter
        instance_dicts = [
            {
                'name': instance.name,
                'status': instance.status,
                'port': instance.port,
                'version': instance.version,
                'data_dir': instance.data_dir
            }
            for instance in instances
        ]
        
        print_instance_table(instance_dicts)
    except Exception as e:
        logger.exception(f"Failed to list instances: {e}")
        raise click.ClickException(f"Failed to list instances: {str(e)}")

@cli.command()
def versions():
    """List all available Foundry VTT versions."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config['base_dir']))
        versions = manager.get_available_versions()
        print_versions_table(versions)
    except Exception as e:
        logger.exception(f"Failed to list versions: {e}")
        raise click.ClickException(f"Failed to list versions: {str(e)}")

@cli.command()
@click.argument('config_file', type=click.Path(exists=True, dir_okay=False))
@click.option('--save', is_flag=True, help='Save the provided config file as the default config')
def apply_config(config_file: str, save: bool):
    """Create instances based on the provided configuration file.
    
    This command will:
    1. Remove any existing instances that are not in the config file
    2. Update any existing instances that don't match the config
    3. Create any new instances specified in the config
    
    CONFIG_FILE: Path to the JSON configuration file
    """
    try:
        # Load the provided config file
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Save the config if requested
        if save:
            from .config import save_config
            save_config(config)
            print_success(f"Saved configuration from {config_file}")
        
        # Create instances from the config
        manager = FoundryInstanceManager()
        
        # Get existing instances before applying config
        existing_instances = manager.list_instances()
        existing_names = {instance.name for instance in existing_instances}
        config_names = set(config.get('instances', {}).keys())
        
        # Show what will be removed
        instances_to_remove = existing_names - config_names
        if instances_to_remove:
            print_warning(f"The following instances will be removed as they're not in the config:")
            for name in instances_to_remove:
                print_warning(f"- {name}")
        
        # Apply the config
        instances = manager.create_instances_from_config(config)
        
        # Show results
        if instances:
            print_success(f"Successfully applied configuration:")
            for instance in instances:
                if instance.name in instances_to_remove:
                    print_info(f"- Removed: {instance.name}")
                elif instance.name in existing_names:
                    print_info(f"- Updated: {instance.name} (v{instance.version})")
                else:
                    print_info(f"- Created: {instance.name} (v{instance.version})")
        else:
            print_info("No instances were created or updated from config")
            
    except json.JSONDecodeError:
        print_error(f"Invalid JSON in config file: {config_file}")
        raise click.Abort()
    except Exception as e:
        print_error(f"Error applying config: {e}")
        raise click.Abort()

if __name__ == '__main__':
    cli() 