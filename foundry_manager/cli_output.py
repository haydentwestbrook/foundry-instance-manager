"""CLI output formatting and display utilities."""

from typing import Dict, List

from rich.console import Console
from rich.table import Table

console = Console()


def format_instance_table(instances: List[dict]) -> Table:
    """Format a list of Foundry instances into a table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Port", style="yellow")
    table.add_column("Version", style="blue")
    table.add_column("Data Directory", style="yellow")
    table.add_column("Link", style="cyan")

    for instance in instances:
        status = instance["status"]
        if status == "running":
            status = "[green]running[/green]"
        elif status == "starting":
            status = "[yellow]starting[/yellow]"
        elif status == "exited":
            status = "[red]stopped[/red]"
        else:
            status = f"[yellow]{status}[/yellow]"

        # Create link based on status
        link = (
            f"http://localhost:{instance['port']}"
            if status in ["[green]running[/green]", "[yellow]starting[/yellow]"]
            else "-"
        )

        table.add_row(
            instance["name"],
            status,
            str(instance["port"]),
            instance["version"] or "N/A",
            str(instance["data_dir"]),
            link,
        )

    return table


def format_versions_table(versions: List[Dict[str, str]]) -> Table:
    """Format a list of Foundry versions into a table.

    Args:
        versions: List of version dictionaries containing version information

    Returns:
        A formatted table of versions
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Version", style="cyan")
    table.add_column("Type", style="green")

    for version in versions:
        # Get version string from dictionary
        version_str = version.get("version", "")

        # Determine version type (release, stable, development)
        version_type = "release"
        if "stable" in version_str.lower():
            version_type = "stable"
        elif (
            "dev" in version_str.lower()
            or "alpha" in version_str.lower()
            or "beta" in version_str.lower()
        ):
            version_type = "development"

        table.add_row(version_str, version_type)

    return table


def print_instance_table(instances: List[dict]) -> None:
    """Print a formatted table of Foundry instances."""
    if not instances:
        console.print("No Foundry VTT instances found")
        return

    table = format_instance_table(instances)
    console.print(table)


def print_versions_table(versions: List[Dict[str, str]]) -> None:
    """Print a formatted table of Foundry versions.

    Args:
        versions: List of version dictionaries containing version information
    """
    if not versions:
        console.print("No Foundry VTT versions found")
        return

    table = format_versions_table(versions)
    console.print(table)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")
