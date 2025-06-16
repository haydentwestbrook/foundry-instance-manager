#!/usr/bin/env python3
"""Foundry VTT Instance Manager CLI.

This module provides a command-line interface for managing Foundry VTT instances.
It allows users to create, start, stop, and manage Foundry VTT instances through
a simple command-line interface.

The CLI supports various operations including:
- Setting up the base directory for instance data
- Creating new Foundry VTT instances
- Managing instance lifecycle (start/stop)
- Listing and monitoring instances
- Updating instance configurations

Example usage:
    $ foundry-manager create my-instance
    $ foundry-manager start my-instance
    $ foundry-manager list
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import click
from rich.console import Console
from rich.table import Table

# isort: off
from foundry_manager.cli_output import (
    print_error,
    print_info,
    print_success,
    print_versions_table,
    print_warning,
)

# isort: on
from foundry_manager import __version__
from foundry_manager.asset_manager import AssetManager
from foundry_manager.foundry_instance_manager import FoundryInstanceManager
from foundry_manager.game_system_manager import GameSystemManager
from foundry_manager.module_manager import ModuleManager
from foundry_manager.world_manager import WorldManager

logger = logging.getLogger("foundry-manager")

# Constants
CONFIG_FILE_NAME = ".fim"

console = Console()

instance_manager = None


def get_config_dir() -> Path:
    """Get the configuration directory.

    Returns:
        Path to the configuration directory.
    """
    return Path.home() / CONFIG_FILE_NAME


def get_config_file() -> Path:
    """Get the configuration file path.

    Returns:
        Path to the configuration file.
    """
    return get_config_dir() / "config.json"


def load_config() -> Dict:
    """Load the configuration.

    Returns:
        Dictionary containing the configuration.
    """
    config_file = get_config_file()
    if not config_file.exists():
        return {}
    with open(config_file) as f:
        return json.load(f)


def save_config(config: Dict) -> None:
    """Save the configuration.

    Args:
        config: Configuration to save.
    """
    config_file = get_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)


def get_instance_manager() -> FoundryInstanceManager:
    """Get an instance manager.

    Returns:
        FoundryInstanceManager instance.

    Raises:
        click.ClickException: If the base directory is not set.
    """
    global instance_manager
    if instance_manager is not None:
        return instance_manager
    config = load_config()
    if "base_dir" not in config:
        raise click.ClickException("Base directory not set. Run 'set-base-dir' first.")
    return FoundryInstanceManager(base_dir=Path(config["base_dir"]))


@click.group()
@click.version_option(version=__version__, prog_name="Foundry Instance Manager")
def cli():
    """Foundry VTT Instance Manager CLI."""
    pass


@cli.command()
@click.argument("base_dir", type=click.Path())
def set_base_dir(base_dir: str):
    """Set the base directory for instance data."""
    config = load_config()
    config["base_dir"] = base_dir
    save_config(config)
    click.echo("Base directory set successfully")


@cli.command()
@click.option("--username", prompt=True, hide_input=False)
@click.option("--password", prompt=True, hide_input=True)
def set_credentials(username: str, password: str):
    """Set Foundry VTT credentials."""
    config = load_config()
    config["username"] = username
    config["password"] = password
    save_config(config)
    click.echo("Foundry VTT credentials set successfully")


def _create_instance_impl(name, version, port, admin_key, username, password):
    config = load_config()
    if "base_dir" not in config:
        raise click.ClickException(
            "Base directory not set. Please run 'set-base-dir' first."
        )
    global instance_manager
    manager = instance_manager or FoundryInstanceManager(
        base_dir=Path(config["base_dir"])
    )
    manager.create_instance(
        name=name,
        version=version,
        port=port,
        admin_key=admin_key,
        username=username or config.get("username"),
        password=password or config.get("password"),
    )
    print_success(f"Created instance {name} (v{version})")


@cli.command()
@click.argument("name")
@click.option("--version", help="Foundry VTT version to install")
@click.option("--port", type=int, help="Port to run the instance on")
@click.option("--admin-key", help="Admin access key")
@click.option("--username", help="Admin username")
@click.option("--password", help="Admin password")
def create(
    name: str, version: str, port: int, admin_key: str, username: str, password: str
) -> None:
    try:
        _create_instance_impl(name, version, port, admin_key, username, password)
    except Exception as e:
        import click

        print(f"DEBUG: Caught exception in create command: {e}")
        raise click.ClickException(str(e))


@cli.command()
@click.argument("name")
def start(name: str) -> None:
    """Start a Foundry VTT instance."""
    try:
        config = load_config()
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(config["base_dir"])
        manager.start_instance(name)
        click.echo(f"Instance {name} started successfully")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to start instance: {str(e)}")


@cli.command()
@click.argument("name")
def stop(name: str) -> None:
    """Stop a Foundry VTT instance."""
    try:
        config = load_config()
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(config["base_dir"])
        manager.stop_instance(name)
        click.echo(f"Instance {name} stopped successfully")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to stop instance: {str(e)}")


@cli.command()
@click.argument("name")
def remove(name: str) -> None:
    """Remove a Foundry VTT instance."""
    try:
        config = load_config()
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(config["base_dir"])
        manager.remove_instance(name)
        click.echo(f"Instance {name} removed successfully")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to remove instance: {str(e)}")


@cli.command(name="list")
def list_instances() -> None:
    """List all Foundry VTT instances."""
    try:
        config = load_config()
        if "base_dir" not in config:
            raise click.ClickException(
                "Base directory not set. Please run 'set-base-dir' first."
            )
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(
            base_dir=Path(config["base_dir"])
        )
        instances = manager.list_instances()
        if not instances:
            click.echo("No Foundry VTT instances found")
            return
        for instance in instances:
            if hasattr(instance, "to_dict"):
                instance = instance.to_dict()
            click.echo(
                f"{instance['name']} (v{instance['version']}) - {instance['status']}"
            )
    except Exception as e:
        raise click.ClickException(f"Failed to list instances: {str(e)}")


@cli.command()
def versions():
    """List available Foundry VTT versions."""
    try:
        manager = get_instance_manager()
        # Use list_versions if available, else fallback
        if hasattr(manager, "list_versions"):
            versions = manager.list_versions()
        else:
            versions = manager.get_available_versions()
        if not versions:
            click.echo("No Foundry VTT versions found")
            return
        version_dicts = [{"version": version} for version in versions]
        print_versions_table(version_dicts)
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise click.ClickException(str(e))


def _load_config_file(config_file):
    with open(config_file, "r") as f:
        return json.load(f)


def _save_config_if_requested(config, config_file, save):
    if save:
        from .config import save_config

        save_config(config)
        print_success(f"Saved configuration from {config_file}")


def _show_instances_to_remove(
    existing_names: Set[str], config_names: Set[str]
) -> List[str]:
    """Show instances that will be removed and return their names."""
    instances_to_remove = existing_names - config_names
    if instances_to_remove:
        print_warning("The following instances will be removed:")
        for name in instances_to_remove:
            print_warning(f"  - {name}")
    return list(instances_to_remove)


def _show_apply_results(
    instances: List[Dict[str, Any]],
    instances_to_remove: List[str],
    existing_names: Set[str],
) -> None:
    """Show the results of applying the configuration."""
    if instances:
        print_success("The following instances were created or updated:")
        for instance in instances:
            print_success(f"  - {instance['name']}")
    if instances_to_remove:
        print_success("The following instances were removed:")
        for name in instances_to_remove:
            print_success(f"  - {name}")


@cli.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--save", is_flag=True, help="Save the provided config file as the default config"
)
def apply_config(config_file: str, save: bool) -> None:
    """Apply configuration from a JSON file."""
    try:
        config = _load_config_file(config_file)
        _save_config_if_requested(config, config_file, save)
        manager = FoundryInstanceManager()
        existing_instances = manager.list_instances()
        existing_names = {instance["name"] for instance in existing_instances}
        config_names = set(config.get("instances", {}).keys())
        instances_to_remove = _show_instances_to_remove(existing_names, config_names)
        instances = manager.create_instances_from_config(config)
        _show_apply_results(instances, instances_to_remove, existing_names)
    except json.JSONDecodeError:
        print_error(f"Invalid JSON in config file: {config_file}")
        raise click.Abort()
    except Exception as e:
        print_error(f"Error applying config: {e}")
        raise click.Abort()


@cli.group()
def systems() -> None:
    """Manage game systems."""
    pass


@systems.command(name="list")
@click.argument("instance")
def list_systems(instance: str) -> None:
    """List installed game systems for an instance."""
    try:
        config = load_config()
        if "base_dir" not in config:
            raise click.ClickException(
                "Base directory not set. Please run 'set-base-dir' first."
            )
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(
            base_dir=Path(config["base_dir"])
        )
        systems = manager.list_systems(instance)
        if not systems:
            click.echo("No game systems found")
            return
        for system in systems:
            click.echo(f"{system['id']} - {system['title']} (v{system['version']})")
    except Exception as e:
        raise click.ClickException(f"Failed to list systems: {str(e)}")


@systems.command()
@click.argument("instance")
@click.argument("system_id")
def info_system(instance, system_id):
    """Get information about a specific game system."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        foundry_instance = manager.get_instance(instance)
        if not foundry_instance:
            raise click.ClickException(f"Instance {instance} not found")

        system_manager = GameSystemManager(foundry_instance.data_dir)
        system_info = system_manager.get_system_info(system_id)

        if not system_info:
            raise click.ClickException(f"System {system_id} not found")

        # Print system information
        print_info(f"System: {system_info['title']}")
        print_info(f"ID: {system_info['id']}")
        print_info(f"Version: {system_info['version']}")
        print_info(f"Path: {system_info['path']}")
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise click.ClickException(f"Failed to get system info: {str(e)}")


@systems.command()
@click.argument("instance")
@click.argument("system_url")
def install_system(instance, system_url):
    """Install a game system from a URL."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        foundry_instance = manager.get_instance(instance)
        if not foundry_instance:
            raise click.ClickException(f"Instance {instance} not found")

        system_manager = GameSystemManager(foundry_instance.data_dir)
        system_manager.install_system(foundry_instance, system_url)
        print_success("System installed successfully")
    except Exception as e:
        logger.error(f"Failed to install system: {e}")
        raise click.ClickException(f"Failed to install system: {str(e)}")


@systems.command()
@click.argument("instance")
@click.argument("system_id")
def remove_system(instance, system_id):
    """Remove a game system."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        foundry_instance = manager.get_instance(instance)
        if not foundry_instance:
            raise click.ClickException(f"Instance {instance} not found")

        system_manager = GameSystemManager(foundry_instance.data_dir)
        system_manager.remove_system(foundry_instance, system_id)
        print_success(f"System {system_id} removed successfully")
    except Exception as e:
        logger.error(f"Failed to remove system: {e}")
        raise click.ClickException(f"Failed to remove system: {str(e)}")


@cli.group()
def modules() -> None:
    """Manage modules."""
    pass


@modules.command(name="list")
@click.argument("instance")
def list_modules(instance: str) -> None:
    """List installed modules for an instance."""
    try:
        config = load_config()
        if "base_dir" not in config:
            raise click.ClickException(
                "Base directory not set. Please run 'set-base-dir' first."
            )
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(
            base_dir=Path(config["base_dir"])
        )
        modules = manager.list_modules(instance)
        if not modules:
            click.echo("No modules found")
            return
        for module in modules:
            click.echo(f"{module['id']} - {module['title']} (v{module['version']})")
    except Exception as e:
        raise click.ClickException(f"Failed to list modules: {str(e)}")


@modules.command()
@click.argument("instance")
@click.argument("module_id")
def info_module(instance, module_id):
    """Get information about a specific module."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_info = manager.get_instance_info(instance)

        if not instance_info:
            raise click.ClickException(f"Instance {instance} not found")

        module_manager = ModuleManager(
            manager.docker_client, instance, Path(config["base_dir"]) / instance
        )

        module_info = module_manager.get_module_info(module_id)

        if not module_info:
            raise click.ClickException(f"Module {module_id} not found")

        table = Table(title=f"Module Information: {module_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in module_info.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            table.add_row(key, str(value))

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to get module info: {e}")
        raise click.ClickException(f"Failed to get module info: {str(e)}")


@modules.command()
@click.argument("instance")
@click.argument("module_url")
def install_module(instance, module_url):
    """Install a module from a URL."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_info = manager.get_instance_info(instance)

        if not instance_info:
            raise click.ClickException(f"Instance {instance} not found")

        module_manager = ModuleManager(
            manager.docker_client, instance, Path(config["base_dir"]) / instance
        )

        module_info = module_manager.install_module(module_url)
        print_success(f"Module {module_info['id']} installed successfully")
    except Exception as e:
        logger.error(f"Failed to install module: {e}")
        raise click.ClickException(f"Failed to install module: {str(e)}")


@modules.command()
@click.argument("instance")
@click.argument("module_id")
def remove_module(instance, module_id):
    """Remove a module from an instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_info = manager.get_instance_info(instance)

        if not instance_info:
            raise click.ClickException(f"Instance {instance} not found")

        module_manager = ModuleManager(
            manager.docker_client, instance, Path(config["base_dir"]) / instance
        )

        module_manager.remove_module(module_id)
        print_success(f"Module {module_id} removed successfully")
    except Exception as e:
        logger.error(f"Failed to remove module: {e}")
        raise click.ClickException(f"Failed to remove module: {str(e)}")


@cli.group()
def worlds() -> None:
    """Manage worlds."""
    pass


@worlds.command(name="list")
@click.argument("instance")
def list_worlds(instance: str) -> None:
    """List worlds for an instance."""
    try:
        config = load_config()
        if "base_dir" not in config:
            raise click.ClickException(
                "Base directory not set. Please run 'set-base-dir' first."
            )
        global instance_manager
        manager = instance_manager or FoundryInstanceManager(
            base_dir=Path(config["base_dir"])
        )
        worlds = manager.list_worlds(instance)
        if not worlds:
            click.echo("No worlds found")
            return
        for world in worlds:
            click.echo(f"{world['id']} - {world['title']} (v{world['version']})")
    except Exception as e:
        raise click.ClickException(f"Failed to list worlds: {str(e)}")


@worlds.command()
@click.argument("instance")
@click.argument("world_id")
def info_world(instance, world_id):
    """Get detailed information about a specific world."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_path = manager.get_instance_path(instance)

        if not instance_path:
            print_error(f"Instance {instance} not found")
            return

        world_manager = WorldManager(instance_path)
        world_info = world_manager.get_world_info(world_id)

        if not world_info:
            print_error(f"World {world_id} not found")
            return

        table = Table(title=f"World Information: {world_info['name']}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in world_info.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to get world info: {e}")
        raise click.ClickException(f"Failed to get world info: {str(e)}")


@worlds.command()
@click.argument("instance")
@click.argument("name")
@click.argument("system")
@click.option("--description", help="World description")
def create_world(instance, name, system, description):
    """Create a new world in a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_path = manager.get_instance_path(instance)

        if not instance_path:
            print_error(f"Instance {instance} not found")
            return

        world_manager = WorldManager(instance_path)
        world_id = world_manager.create_world(name, system, description)

        if world_id:
            print_success(f"World {name} created successfully with ID: {world_id}")
        else:
            print_error("Failed to create world")
    except Exception as e:
        logger.error(f"Failed to create world: {e}")
        raise click.ClickException(f"Failed to create world: {str(e)}")


@worlds.command()
@click.argument("instance")
@click.argument("world_id")
@click.option("--backup-path", type=click.Path(), help="Path to store the backup")
def backup_world(instance, world_id, backup_path):
    """Create a backup of a world."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_path = manager.get_instance_path(instance)

        if not instance_path:
            print_error(f"Instance {instance} not found")
            return

        world_manager = WorldManager(instance_path)
        backup_file = world_manager.backup_world(
            world_id, Path(backup_path) if backup_path else None
        )

        if backup_file:
            print_success(f"World backup created successfully at: {backup_file}")
        else:
            print_error("Failed to create world backup")
    except Exception as e:
        logger.error(f"Failed to backup world: {e}")
        raise click.ClickException(f"Failed to backup world: {str(e)}")


@worlds.command()
@click.argument("instance")
@click.argument("backup_path", type=click.Path(exists=True))
def restore_world(instance, backup_path):
    """Restore a world from a backup."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_path = manager.get_instance_path(instance)

        if not instance_path:
            print_error(f"Instance {instance} not found")
            return

        world_manager = WorldManager(instance_path)
        world_id = world_manager.restore_world(Path(backup_path))

        if world_id:
            print_success(f"World restored successfully with ID: {world_id}")
        else:
            print_error("Failed to restore world")
    except Exception as e:
        logger.error(f"Failed to restore world: {e}")
        raise click.ClickException(f"Failed to restore world: {str(e)}")


@worlds.command()
@click.argument("instance")
@click.argument("world_id")
def remove_world(instance, world_id):
    """Remove a world from a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_path = manager.get_instance_path(instance)

        if not instance_path:
            print_error(f"Instance {instance} not found")
            return

        world_manager = WorldManager(instance_path)
        if world_manager.remove_world(world_id):
            print_success(f"World {world_id} removed successfully")
        else:
            print_error(f"Failed to remove world {world_id}")
    except Exception as e:
        logger.error(f"Failed to remove world: {e}")
        raise click.ClickException(f"Failed to remove world: {str(e)}")


@cli.group()
def assets():
    """Manage shared assets."""
    pass


@assets.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--metadata", help="JSON metadata for the asset")
@click.option("--skip-optimization", is_flag=True, help="Skip asset optimization")
def upload(file_path, metadata, skip_optimization):
    """Upload an asset to the shared directory."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        asset_manager = AssetManager(manager.base_dir)

        if skip_optimization:
            asset_manager.processor.disable_processing = True

        asset_id = asset_manager.upload_asset(file_path, metadata)
        if asset_id:
            print_success(f"Asset uploaded successfully with ID: {asset_id}")

            # Show optimization results
            asset_info = asset_manager.get_asset_info(asset_id)
            if asset_info["original_size"] != asset_info["processed_size"]:
                reduction = (
                    1 - asset_info["processed_size"] / asset_info["original_size"]
                ) * 100
                print_info(f"Size reduced by {reduction:.1f}%")
                print_info(f"Original: {asset_info['original_size'] / 1024:.1f}KB")
                print_info(f"Processed: {asset_info['processed_size'] / 1024:.1f}KB")
                print_info(f"Format: {asset_info['format']}")
        else:
            print_error("Failed to upload asset")
    except Exception as e:
        logger.error(f"Failed to upload asset: {e}")
        raise click.ClickException(f"Failed to upload asset: {str(e)}")


@assets.command("list")
@click.option("--type", help="Filter assets by type")
def list_assets(type):
    """List all assets or assets of a specific type."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        asset_manager = AssetManager(manager.base_dir)

        assets = asset_manager.list_assets(type)
        if not assets:
            print_info("No assets found")
            return

        # Create a table of assets
        table = Table(title="Shared Assets")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Size", style="blue")
        table.add_column("Uploaded", style="magenta")

        for asset in assets:
            size_mb = asset["size"] / (1024 * 1024)
            table.add_row(
                asset["id"],
                asset["name"],
                asset["type"],
                f"{size_mb:.2f} MB",
                asset["uploaded"],
            )

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise click.ClickException(f"Failed to list assets: {str(e)}")


@assets.command()
@click.argument("asset_id")
def info(asset_id):
    """Get detailed information about a specific asset."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        asset_manager = AssetManager(manager.base_dir)

        asset_info = asset_manager.get_asset_info(asset_id)
        if not asset_info:
            print_error(f"Asset {asset_id} not found")
            return

        # Print asset information
        print_info(f"Asset ID: {asset_info['id']}")
        print_info(f"Name: {asset_info['name']}")
        print_info(f"Type: {asset_info['type']}")
        print_info(f"Size: {asset_info['size'] / (1024 * 1024):.2f} MB")
        print_info(f"Uploaded: {asset_info['uploaded']}")
        if asset_info["metadata"]:
            print_info("Metadata:")
            for key, value in asset_info["metadata"].items():
                print_info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"Failed to get asset info: {e}")
        raise click.ClickException(f"Failed to get asset info: {str(e)}")


@assets.command("remove")
@click.argument("asset_id")
def remove_asset(asset_id):
    """Remove an asset from the shared directory."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        asset_manager = AssetManager(manager.base_dir)

        if asset_manager.remove_asset(asset_id):
            print_success(f"Asset {asset_id} removed successfully")
        else:
            print_error(f"Failed to remove asset {asset_id}")
    except Exception as e:
        logger.error(f"Failed to remove asset: {e}")
        raise click.ClickException(f"Failed to remove asset: {str(e)}")


@cli.command()
@click.argument("name")
@click.option("--version", required=True, help="New Foundry VTT version")
def migrate(name: str, version: str) -> None:
    """Migrate a Foundry VTT instance to a new version."""
    try:
        manager = get_instance_manager()
        manager.migrate_instance(name, version)
        click.echo(f"Instance {name} migrated to version {version} successfully")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to migrate instance: {str(e)}")


@cli.command()
@click.argument("name")
@click.option("--admin-key", help="Admin access key")
@click.option("--username", help="Foundry VTT username")
@click.option("--password", help="Foundry VTT password")
def config(
    name: str,
    admin_key: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Apply configuration to a Foundry VTT instance."""
    try:
        manager = get_instance_manager()
        # Build a config dict for a single instance
        config_dict = {
            "instances": {
                name: {
                    "admin_key": admin_key or "",
                    "username": username or "",
                    "password": password or "",
                }
            }
        }
        manager.apply_config(config_dict)
        click.echo(f"Configuration applied to instance {name} successfully")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to apply configuration: {str(e)}")


if __name__ == "__main__":
    cli()
