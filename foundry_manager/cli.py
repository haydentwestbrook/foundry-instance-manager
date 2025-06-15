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

import click
from rich.console import Console
from rich.table import Table

from foundry_manager.cli_output import (
    print_error,
    print_info,
    print_instance_table,
    print_success,
    print_versions_table,
    print_warning,
)
from foundry_manager.foundry_instance_manager import FoundryInstanceManager
from foundry_manager.game_system_manager import GameSystemManager
from foundry_manager.module_manager import ModuleManager

logger = logging.getLogger("foundry-manager")

# Constants
CONFIG_FILE_NAME = ".fim"

console = Console()


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

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


@click.group()
def cli():
    """Foundry VTT Instance Manager CLI."""
    pass


@cli.command()
@click.option("--base-dir", help="Base directory for container data")
def set_base_dir(base_dir):
    """Set the base directory for Foundry VTT instances."""
    try:
        config = load_config()
        config["base_dir"] = base_dir
        save_config(config)
        print_success("Base directory set successfully")
    except Exception as e:
        logger.error(f"Failed to set base directory: {e}")
        raise click.ClickException("Failed to set base directory")


@cli.command()
@click.option("--username", help="Foundry VTT username")
@click.option("--password", help="Foundry VTT password")
def set_credentials(username, password):
    """Set the Foundry VTT username and password."""
    try:
        config = load_config()
        config["foundry_username"] = username
        config["foundry_password"] = password
        save_config(config)
        print_success("Foundry VTT credentials set successfully")
    except Exception as e:
        logger.error(f"Failed to set credentials: {e}")
        raise click.ClickException("Failed to set credentials")


@cli.command()
@click.argument("name")
@click.option("--version", help="Foundry VTT version")
@click.option(
    "--port",
    type=int,
    help="Host port to map to Foundry's internal port 30000 (default: 30000)",
    default=30000,
)
@click.option(
    "--environment", multiple=True, help="Environment variables in the format KEY=VALUE"
)
@click.option("--admin-key", envvar="FOUNDRY_ADMIN_KEY", help="Foundry VTT admin key")
@click.option("--proxy-port", default=443, help="Foundry VTT proxy port")
@click.option("--proxy-ssl/--no-proxy-ssl", default=True, help="Enable SSL proxy")
@click.option("--minify/--no-minify", default=True, help="Minify static files")
@click.option(
    "--update-channel",
    default="release",
    type=click.Choice(["release", "stable", "development"]),
    help="Update channel",
)
def create(
    name,
    version,
    port,
    environment,
    admin_key,
    proxy_port,
    proxy_ssl,
    minify,
    update_channel,
):
    """Create a new Foundry VTT instance."""
    try:
        env_dict = dict(e.split("=", 1) for e in environment)
        config = load_config()

        # Validate required credentials
        if not config.get("foundry_username") or not config.get("foundry_password"):
            print_error("Foundry VTT credentials not set")
            raise click.ClickException(
                "Foundry VTT credentials not set. Use 'set-credentials' command first."
            )

        # Set Foundry-specific environment variables
        env_dict.update(
            {
                "FOUNDRY_USERNAME": config.get("foundry_username", ""),
                "FOUNDRY_PASSWORD": config.get("foundry_password", ""),
                "FOUNDRY_ADMIN_KEY": admin_key,
                "FOUNDRY_PROXY_PORT": str(proxy_port),
                "FOUNDRY_PROXY_SSL": str(proxy_ssl).lower(),
                "FOUNDRY_MINIFY_STATIC_FILES": str(minify).lower(),
                "FOUNDRY_UPDATE_CHANNEL": update_channel,
                "FOUNDRY_DATA_PATH": "/data",
                "FOUNDRY_HOSTNAME": "0.0.0.0",
                "FOUNDRY_PORT": "30000",
            }
        )

        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))

        # Create instance
        manager.create_instance(
            name=name, version=version, port=port, environment=env_dict
        )

        print_success(f"Instance {name} created successfully")
        print_info("Access Foundry VTT at:")
        print_info(f"HTTP:  http://localhost:{port}")
        if proxy_ssl:
            print_info(f"HTTPS: https://localhost:{proxy_port}")
    except Exception as e:
        logger.error(f"Failed to create instance: {e}")
        raise click.ClickException(f"Failed to create instance: {str(e)}")


@cli.command()
@click.argument("name")
def start(name):
    """Start a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        manager.start_instance(name)
        print_success(f"Instance {name} started successfully")
    except Exception as e:
        logger.error(f"Failed to start instance: {e}")
        raise click.ClickException(f"Failed to start instance: {str(e)}")


@cli.command()
@click.argument("name")
def stop(name):
    """Stop a Foundry VTT instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        manager.stop_instance(name)
        print_success(f"Instance {name} stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop instance: {e}")
        raise click.ClickException(f"Failed to stop instance: {str(e)}")


@cli.command()
@click.argument("name")
def remove(name):
    """Remove a Foundry VTT instance and its data."""
    confirm_msg = (
        f"Warning: Removing instance '{name}' will delete all data associated with "
        "this Foundry server. Are you sure you want to proceed?"
    )
    if not click.confirm(confirm_msg, default=False):
        return
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        manager.remove_instance(name)
        print_success(f"Instance {name} removed successfully.")
    except Exception as e:
        logger.error(f"Failed to remove instance: {e}")
        raise click.ClickException(f"Failed to remove instance: {str(e)}")


@cli.command()
@click.argument("name")
@click.argument("version")
def migrate(name, version):
    """Migrate a Foundry VTT instance to a new version."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        manager.migrate_instance(name, version)
        print_success(f"Instance {name} migrated to version {version} successfully")
    except Exception as e:
        logger.error(f"Failed to migrate instance: {e}")
        raise click.ClickException(f"Failed to migrate instance: {str(e)}")


@cli.command()
def list_instances():
    """List all Foundry VTT instances and their status."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instances = manager.list_instances()

        # Convert instances to dictionaries for the table formatter
        instance_dicts = [
            {
                "name": instance.name,
                "status": instance.status,
                "port": instance.port,
                "version": instance.version,
                "data_dir": instance.data_dir,
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
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        versions = manager.get_available_versions()
        print_versions_table(versions)
    except Exception as e:
        logger.exception(f"Failed to list versions: {e}")
        raise click.ClickException(f"Failed to list versions: {str(e)}")


def _load_config_file(config_file):
    with open(config_file, "r") as f:
        return json.load(f)


def _save_config_if_requested(config, config_file, save):
    if save:
        from .config import save_config

        save_config(config)
        print_success(f"Saved configuration from {config_file}")


def _show_instances_to_remove(existing_names, config_names):
    instances_to_remove = existing_names - config_names
    if instances_to_remove:
        print_warning(
            """'The following instances will be removed
                as they're not in the config:"""
        )
        for name in instances_to_remove:
            print_warning(f"- {name}")
    return instances_to_remove


def _show_apply_results(instances, instances_to_remove, existing_names):
    if instances:
        print_success("Successfully applied configuration:")
        for instance in instances:
            if instance.name in instances_to_remove:
                print_info(f"- Removed: {instance.name}")
            elif instance.name in existing_names:
                print_info(f"- Updated: {instance.name} (v{instance.version})")
            else:
                print_info(f"- Created: {instance.name} (v{instance.version})")
    else:
        print_info("No instances were created or updated from config")


@cli.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--save", is_flag=True, help="Save the provided config file as the default config"
)
def apply_config(config_file: str, save: bool):
    """Create instances based on the provided configuration file.

    This command will:
    1. Remove any existing instances that are not in the config file
    2. Update any existing instances that don't match the config
    3. Create any new instances specified in the config

    CONFIG_FILE: Path to the JSON configuration file
    """
    try:
        config = _load_config_file(config_file)
        _save_config_if_requested(config, config_file, save)
        manager = FoundryInstanceManager()
        existing_instances = manager.list_instances()
        existing_names = {instance.name for instance in existing_instances}
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
def systems():
    """Manage game systems for Foundry VTT instances."""
    pass


@systems.command()
@click.argument("instance")
def list_systems(instance):
    """List all game systems installed in an instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        foundry_instance = manager.get_instance(instance)
        if not foundry_instance:
            raise click.ClickException(f"Instance {instance} not found")

        system_manager = GameSystemManager(foundry_instance.data_dir)
        systems = system_manager.list_systems()

        # Determine the active system from options.json
        options_path = foundry_instance.data_dir / "Data" / "options.json"
        active_system = None
        if options_path.exists():
            try:
                with open(options_path) as f:
                    options = json.load(f)
                    active_system = options.get("system")
            except Exception as e:
                logger.warning(f"Could not read options.json: {e}")

        if not systems:
            print_info("No game systems installed")
            return

        # Create a table of systems
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Version", style="yellow")

        for system in systems:
            title = system["title"]
            if active_system and system["id"] == active_system:
                title += " ★"
            table.add_row(
                system["id"],
                title,
                system["version"],
            )

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to list game systems: {e}")
        raise click.ClickException(f"Failed to list game systems: {str(e)}")


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
        system_manager.install_system(system_url)
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
        system_manager.remove_system(system_id)
        print_success(f"System {system_id} removed successfully")
    except Exception as e:
        logger.error(f"Failed to remove system: {e}")
        raise click.ClickException(f"Failed to remove system: {str(e)}")


@cli.group()
def modules():
    """Manage Foundry VTT modules."""
    pass


@modules.command()
@click.argument("instance")
def list_modules(instance):
    """List all installed modules in an instance."""
    try:
        config = load_config()
        manager = FoundryInstanceManager(base_dir=Path(config["base_dir"]))
        instance_info = manager.get_instance_info(instance)

        if not instance_info:
            raise click.ClickException(f"Instance {instance} not found")

        module_manager = ModuleManager(
            manager.docker_client, instance, Path(config["base_dir"]) / instance
        )

        modules = module_manager.list_modules()

        if not modules:
            print_info("No modules installed")
            return

        table = Table(title=f"Modules in {instance}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Author", style="blue")

        for module in modules:
            table.add_row(
                module.get("id", ""),
                module.get("title", ""),
                module.get("version", ""),
                module.get("author", ""),
            )

        console.print(table)
    except Exception as e:
        logger.error(f"Failed to list modules: {e}")
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


if __name__ == "__main__":
    cli()
