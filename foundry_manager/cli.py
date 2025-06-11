#!/usr/bin/env python3

import click
from pathlib import Path
from rich.table import Table
from .docker_manager import DockerManager

@click.group()
@click.option('--base-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
              help='Base directory for container data (defaults to current directory)')
@click.pass_context
def cli(ctx, base_dir):
    """Docker Container Manager CLI"""
    ctx.ensure_object(dict)
    ctx.obj['base_dir'] = base_dir

@cli.command()
@click.option('--name', required=True, help='Name of the container')
@click.option('--version', help='Specific Foundry VTT version to use')
@click.option('--image', help='Custom Docker image to use (overrides version)')
@click.pass_context
def create(ctx, name, version, image):
    """Create a new Foundry VTT container"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.create_container(name, image=image, version=version)

@cli.command()
def versions():
    """List available Foundry VTT versions"""
    manager = DockerManager()
    versions = manager.get_available_versions()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Version")
    table.add_column("Last Updated")
    
    for version in versions:
        table.add_row(
            version['version'],
            version['last_updated']
        )
    
    console.print(table)

@cli.command()
@click.pass_context
def list(ctx):
    """List all containers"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.list_containers()

@cli.command()
@click.option('--name', required=True, help='Name of the container')
@click.pass_context
def start(ctx, name):
    """Start a container"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.start_container(name)

@cli.command()
@click.option('--name', required=True, help='Name of the container')
@click.pass_context
def stop(ctx, name):
    """Stop a container"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.stop_container(name)

@cli.command()
@click.option('--name', required=True, help='Name of the container')
@click.pass_context
def remove(ctx, name):
    """Remove a container"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.remove_container(name)

@cli.command()
@click.option('--name', required=True, help='Name of the container')
@click.option('--version', required=True, help='New Foundry VTT version')
@click.pass_context
def migrate(ctx, name, version):
    """Migrate a container to a new Foundry VTT version"""
    manager = DockerManager(ctx.obj.get('base_dir'))
    manager.migrate_container(name, version)

if __name__ == '__main__':
    cli(obj={}) 