#!/usr/bin/env python3
"""Unit tests for the AssetManager class."""

import pytest

from foundry_manager.asset_manager import AssetManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def asset_manager(temp_dir):
    """Create an AssetManager instance for testing."""
    return AssetManager(temp_dir)


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample image file for testing."""
    image_path = temp_dir / "test_image.png"
    image_path.write_bytes(b"fake image data")
    return image_path


@pytest.fixture
def sample_audio(temp_dir):
    """Create a sample audio file for testing."""
    audio_path = temp_dir / "test_audio.mp3"
    audio_path.write_bytes(b"fake audio data")
    return audio_path


def test_asset_manager_initialization(temp_dir):
    """Test AssetManager initialization."""
    AssetManager(temp_dir)

    # Check if directories were created
    assert (temp_dir / "shared_assets").exists()
    assert (temp_dir / "shared_assets" / "images").exists()
    assert (temp_dir / "shared_assets" / "audio").exists()
    assert (temp_dir / "shared_assets" / "video").exists()
    assert (temp_dir / "shared_assets" / "documents").exists()
    assert (temp_dir / "shared_assets" / "models").exists()
    assert (temp_dir / "shared_assets" / "other").exists()

    # Check if index file was created
    assert (temp_dir / "shared_assets" / "asset_index.json").exists()


def test_upload_asset(asset_manager, sample_image):
    """Test asset upload functionality."""
    metadata = {"description": "Test image", "tags": ["test"]}
    asset_id = asset_manager.upload_asset(sample_image, metadata)

    assert asset_id is not None
    assert asset_id in asset_manager.asset_index

    asset_info = asset_manager.asset_index[asset_id]
    assert asset_info["name"] == "test_image.png"
    assert asset_info["type"] == "images"
    assert asset_info["metadata"] == metadata


def test_upload_nonexistent_file(asset_manager):
    """Test uploading a nonexistent file."""
    asset_id = asset_manager.upload_asset("nonexistent.png")
    assert asset_id is None


def test_list_assets(asset_manager, sample_image, sample_audio):
    """Test listing assets."""
    # Upload some assets
    asset_manager.upload_asset(sample_image)
    asset_manager.upload_asset(sample_audio)

    # List all assets
    all_assets = asset_manager.list_assets()
    assert len(all_assets) == 2

    # List by type
    image_assets = asset_manager.list_assets("images")
    assert len(image_assets) == 1
    assert image_assets[0]["type"] == "images"

    audio_assets = asset_manager.list_assets("audio")
    assert len(audio_assets) == 1
    assert audio_assets[0]["type"] == "audio"


def test_get_asset_info(asset_manager, sample_image):
    """Test getting asset information."""
    asset_id = asset_manager.upload_asset(sample_image)
    asset_info = asset_manager.get_asset_info(asset_id)

    assert asset_info is not None
    assert asset_info["id"] == asset_id
    assert asset_info["name"] == "test_image.png"
    assert asset_info["type"] == "images"


def test_get_nonexistent_asset_info(asset_manager):
    """Test getting information for a nonexistent asset."""
    asset_info = asset_manager.get_asset_info("nonexistent")
    assert asset_info is None


def test_remove_asset(asset_manager, sample_image):
    """Test removing an asset."""
    asset_id = asset_manager.upload_asset(sample_image)
    assert asset_manager.remove_asset(asset_id)
    assert asset_id not in asset_manager.asset_index

    # Try to remove again
    assert not asset_manager.remove_asset(asset_id)


def test_get_asset_path(asset_manager, sample_image):
    """Test getting asset path."""
    asset_id = asset_manager.upload_asset(sample_image)
    asset_path = asset_manager.get_asset_path(asset_id)

    assert asset_path is not None
    assert asset_path.exists()
    assert asset_path.suffix == ".png"


def test_get_nonexistent_asset_path(asset_manager):
    """Test getting path for a nonexistent asset."""
    asset_path = asset_manager.get_asset_path("nonexistent")
    assert asset_path is None


def test_asset_type_detection(asset_manager, temp_dir):
    """Test asset type detection for different file types."""
    test_files = {
        "test.jpg": "images",
        "test.png": "images",
        "test.webp": "images",
        "test.mp3": "audio",
        "test.ogg": "audio",
        "test.wav": "audio",
        "test.mp4": "video",
        "test.webm": "video",
        "test.pdf": "documents",
        "test.html": "documents",
        "test.json": "documents",
        "test.glb": "models",
        "test.gltf": "models",
        "test.xyz": "other",  # Unknown extension
    }

    for filename, expected_type in test_files.items():
        file_path = temp_dir / filename
        file_path.write_bytes(b"test data")
        assert asset_manager._get_asset_type(file_path) == expected_type
