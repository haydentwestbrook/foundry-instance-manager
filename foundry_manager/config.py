"""Configuration management for Foundry Instance Manager."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = "fim_config.json"


def load_config() -> dict:
    """Load configuration from the config file."""
    config_path = Path.home() / CONFIG_FILE

    if not config_path.exists():
        # Create default config
        config = {
            "base_dir": str(Path.home() / "foundry-instances"),
            "shared_dir": str(Path.home() / "foundry-shared"),
            "instances": {},  # Dictionary of instance configurations
        }
        save_config(config)
        return config

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def save_config(config: dict) -> None:
    """Save configuration to the config file."""
    config_path = Path.home() / CONFIG_FILE

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise


def get_base_dir() -> Path:
    """Get the base directory for Foundry instances."""
    config = load_config()
    return Path(config["base_dir"])


def get_shared_dir() -> Path:
    """Get the shared directory for Foundry instances."""
    config = load_config()
    return Path(config["shared_dir"])


def get_instances() -> Dict[str, dict]:
    """Get all instance configurations."""
    config = load_config()
    return config.get("instances", {})


def add_instance(
    name: str,
    version: str,
    data_dir: Optional[str] = None,
    port: int = 30000,
    environment: Optional[Dict[str, str]] = None,
) -> None:
    """Add an instance configuration."""
    config = load_config()
    if "instances" not in config:
        config["instances"] = {}

    config["instances"][name] = {
        "version": version,
        "data_dir": data_dir or str(Path(config["base_dir"]) / name),
        "port": port,
        "environment": environment or {},
    }

    save_config(config)


def remove_instance(name: str) -> None:
    """Remove an instance configuration."""
    config = load_config()
    if "instances" in config and name in config["instances"]:
        del config["instances"][name]
        save_config(config)
