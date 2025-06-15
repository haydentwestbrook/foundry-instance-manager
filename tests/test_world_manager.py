#!/usr/bin/env python3
"""Tests for the WorldManager class."""

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from foundry_manager.world_manager import WorldManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def world_manager(temp_dir):
    """Create a WorldManager instance with a temporary directory."""
    instance_path = temp_dir / "instance"
    instance_path.mkdir(parents=True)
    return WorldManager(instance_path)


@pytest.fixture
def sample_world_data():
    """Create sample world data for testing."""
    return {
        "id": "test-world",
        "name": "Test World",
        "system": "dnd5e",
        "description": "A test world",
        "coreVersion": "11.0.0",
        "systemVersion": "2.0.0",
        "lastModified": datetime.now().isoformat(),
    }


def test_list_worlds_empty(world_manager):
    """Test listing worlds when none exist."""
    worlds = world_manager.list_worlds()
    assert len(worlds) == 0


def test_list_worlds(world_manager, sample_world_data):
    """Test listing worlds when some exist."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    worlds = world_manager.list_worlds()
    assert len(worlds) == 1
    assert worlds[0]["id"] == sample_world_data["id"]
    assert worlds[0]["name"] == sample_world_data["name"]
    assert worlds[0]["system"] == sample_world_data["system"]


def test_get_world_info_nonexistent(world_manager):
    """Test getting info for a nonexistent world."""
    info = world_manager.get_world_info("nonexistent")
    assert info is None


def test_get_world_info(world_manager, sample_world_data):
    """Test getting info for an existing world."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    info = world_manager.get_world_info(sample_world_data["id"])
    assert info is not None
    assert info["id"] == sample_world_data["id"]
    assert info["name"] == sample_world_data["name"]
    assert info["system"] == sample_world_data["system"]
    assert info["description"] == sample_world_data["description"]


def test_create_world(world_manager):
    """Test creating a new world."""
    world_id = world_manager.create_world("Test World", "dnd5e", "A test world")
    assert world_id is not None
    assert world_id == "test-world"

    # Verify world directory and files exist
    world_dir = world_manager.worlds_path / world_id
    assert world_dir.exists()
    assert (world_dir / "world.json").exists()

    # Verify world.json contents
    with open(world_dir / "world.json") as f:
        data = json.load(f)
        assert data["id"] == world_id
        assert data["name"] == "Test World"
        assert data["system"] == "dnd5e"
        assert data["description"] == "A test world"


def test_create_world_existing(world_manager, sample_world_data):
    """Test creating a world that already exists."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    # Try to create a world with the same name
    world_id = world_manager.create_world("Test World", "dnd5e")
    assert world_id is None


def test_backup_world_nonexistent(world_manager):
    """Test backing up a nonexistent world."""
    backup_path = world_manager.backup_world("nonexistent")
    assert backup_path is None


def test_backup_world(world_manager, sample_world_data):
    """Test backing up an existing world."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    # Create a backup
    backup_path = world_manager.backup_world(sample_world_data["id"])
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.suffix == ".zip"


def test_restore_world_nonexistent(world_manager):
    """Test restoring from a nonexistent backup."""
    world_id = world_manager.restore_world(Path("nonexistent.zip"))
    assert world_id is None


def test_restore_world(world_manager, sample_world_data, temp_dir):
    """Test restoring from a valid backup."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    # Create a backup
    backup_path = world_manager.backup_world(sample_world_data["id"])
    assert backup_path is not None

    # Remove the original world
    shutil.rmtree(world_dir)

    # Restore from backup
    world_id = world_manager.restore_world(backup_path)
    assert world_id is not None
    assert world_id == sample_world_data["id"]

    # Verify restored world
    restored_dir = world_manager.worlds_path / world_id
    assert restored_dir.exists()
    assert (restored_dir / "world.json").exists()

    with open(restored_dir / "world.json") as f:
        data = json.load(f)
        assert data["id"] == sample_world_data["id"]
        assert data["name"] == sample_world_data["name"]


def test_remove_world_nonexistent(world_manager):
    """Test removing a nonexistent world."""
    result = world_manager.remove_world("nonexistent")
    assert result is False


def test_remove_world(world_manager, sample_world_data):
    """Test removing an existing world."""
    # Create a test world
    world_dir = world_manager.worlds_path / sample_world_data["id"]
    world_dir.mkdir(parents=True)

    with open(world_dir / "world.json", "w") as f:
        json.dump(sample_world_data, f)

    # Remove the world
    result = world_manager.remove_world(sample_world_data["id"])
    assert result is True
    assert not world_dir.exists()
