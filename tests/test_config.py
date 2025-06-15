"""Tests for the configuration management functionality."""

import json
from pathlib import Path

import pytest

from foundry_manager.config import (
    get_base_dir,
    get_shared_dir,
    load_config,
    save_config,
)


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Create a temporary config file and set it as the home directory."""
    config_path = tmp_path / "fim_config.json"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return config_path


def test_load_config_default(config_file):
    """Test loading config with default values when file doesn't exist."""
    config = load_config()

    assert config["base_dir"] == str(Path.home() / "foundry-instances")
    assert config["shared_dir"] == str(Path.home() / "foundry-shared")
    assert config_file.exists()


def test_load_config_existing(config_file):
    """Test loading config from existing file."""
    # Create config file with custom values
    config_data = {"base_dir": "/custom/base", "shared_dir": "/custom/shared"}
    config_file.write_text(json.dumps(config_data))

    # Load config
    config = load_config()

    assert config["base_dir"] == "/custom/base"
    assert config["shared_dir"] == "/custom/shared"


def test_save_config(config_file):
    """Test saving config to file."""
    config_data = {"base_dir": "/test/base", "shared_dir": "/test/shared"}

    save_config(config_data)

    # Verify file was created and contains correct data
    assert config_file.exists()
    saved_data = json.loads(config_file.read_text())
    assert saved_data == config_data


def test_get_base_dir(config_file):
    """Test getting base directory from config."""
    # Set up config with custom base directory
    config_data = {"base_dir": "/test/base", "shared_dir": "/test/shared"}
    config_file.write_text(json.dumps(config_data))

    base_dir = get_base_dir()
    assert base_dir == Path("/test/base")


def test_get_shared_dir(config_file):
    """Test getting shared directory from config."""
    # Set up config with custom shared directory
    config_data = {"base_dir": "/test/base", "shared_dir": "/test/shared"}
    config_file.write_text(json.dumps(config_data))

    shared_dir = get_shared_dir()
    assert shared_dir == Path("/test/shared")


def test_config_error_handling(config_file):
    """Test error handling when config file is invalid."""
    # Create invalid JSON
    config_file.write_text("invalid json")

    with pytest.raises(json.JSONDecodeError, match="Expecting value"):
        load_config()
