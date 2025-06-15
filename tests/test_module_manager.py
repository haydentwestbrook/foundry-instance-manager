#!/usr/bin/env python3
"""Tests for the Foundry VTT Module Manager."""

import json
from unittest.mock import MagicMock, patch

import pytest
from docker import DockerClient

from foundry_manager.module_manager import ModuleManager


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    return MagicMock(spec=DockerClient)


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "test_instance"
    data_dir.mkdir()
    modules_dir = data_dir / "Data" / "modules"
    modules_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def module_manager(mock_docker_client, test_data_dir):
    """Create a ModuleManager instance for testing."""
    return ModuleManager(mock_docker_client, "test_instance", test_data_dir)


def test_list_modules_empty(module_manager):
    """Test listing modules when none are installed."""
    modules = module_manager.list_modules()
    assert len(modules) == 0


def test_list_modules(module_manager, test_data_dir):
    """Test listing installed modules."""
    # Create a test module
    module_dir = test_data_dir / "Data" / "modules" / "test-module"
    module_dir.mkdir()

    module_data = {
        "id": "test-module",
        "title": "Test Module",
        "version": "1.0.0",
        "author": "Test Author",
    }

    with open(module_dir / "module.json", "w") as f:
        json.dump(module_data, f)

    modules = module_manager.list_modules()
    assert len(modules) == 1
    assert modules[0]["id"] == "test-module"
    assert modules[0]["title"] == "Test Module"


def test_get_module_info(module_manager, test_data_dir):
    """Test getting information about a specific module."""
    # Create a test module
    module_dir = test_data_dir / "Data" / "modules" / "test-module"
    module_dir.mkdir()

    module_data = {
        "id": "test-module",
        "title": "Test Module",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test module",
    }

    with open(module_dir / "module.json", "w") as f:
        json.dump(module_data, f)

    module_info = module_manager.get_module_info("test-module")
    assert module_info is not None
    assert module_info["id"] == "test-module"
    assert module_info["title"] == "Test Module"
    assert module_info["description"] == "A test module"


def test_get_module_info_not_found(module_manager):
    """Test getting information about a non-existent module."""
    module_info = module_manager.get_module_info("non-existent")
    assert module_info is None


@patch("requests.get")
def test_install_module(mock_get, module_manager, test_data_dir):
    """Test installing a module from a URL."""
    # Mock module manifest
    manifest = {
        "id": "test-module",
        "title": "Test Module",
        "version": "1.0.0",
        "author": "Test Author",
        "download": "https://example.com/module.zip",
    }

    # Mock the manifest response
    mock_manifest_response = MagicMock()
    mock_manifest_response.json.return_value = manifest
    mock_manifest_response.raise_for_status.return_value = None

    # Create a valid mock ZIP file
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("module.json", json.dumps(manifest))
        zip_file.writestr(
            "README.md", "# Test Module\n\nA test module for Foundry VTT."
        )

    # Mock the download response
    mock_download_response = MagicMock()
    mock_download_response.content = zip_buffer.getvalue()
    mock_download_response.raise_for_status.return_value = None

    # Configure the mock to return different responses for different URLs
    mock_get.side_effect = [mock_manifest_response, mock_download_response]

    # Install the module
    installed_module = module_manager.install_module("https://example.com/module.json")

    # Verify the module was installed
    assert installed_module["id"] == "test-module"
    module_dir = test_data_dir / "Data" / "modules" / "test-module"
    assert (module_dir / "module.json").exists()
    assert (module_dir / "README.md").exists()

    # Verify the requests were made
    assert mock_get.call_count == 2
    mock_get.assert_any_call("https://example.com/module.json")
    mock_get.assert_any_call("https://example.com/module.zip")


def test_remove_module(module_manager, test_data_dir):
    """Test removing a module."""
    # Create a test module
    module_dir = test_data_dir / "Data" / "modules" / "test-module"
    module_dir.mkdir()

    module_data = {"id": "test-module", "title": "Test Module"}

    with open(module_dir / "module.json", "w") as f:
        json.dump(module_data, f)

    # Remove the module
    module_manager.remove_module("test-module")

    # Verify the module was removed
    assert not module_dir.exists()


def test_remove_module_not_found(module_manager):
    """Test removing a non-existent module."""
    with pytest.raises(ValueError, match="Module non-existent not found"):
        module_manager.remove_module("non-existent")
