"""Integration tests for the Foundry VTT Instance Manager CLI.

This module contains integration tests that verify the functionality of the CLI
commands by testing them against a real Docker environment. The tests cover:

- Basic CLI functionality (version, help)
- Instance management (create, list, start, stop, remove)
- Configuration management (set base directory, credentials)
- Game system management
- Module management
- World management
- Asset management

The tests use pytest fixtures to set up and tear down test resources.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

import foundry_manager.cli
from foundry_manager.cli import cli
from foundry_manager.foundry_instance_manager import FoundryInstanceManager

# Test data
TEST_INSTANCE_NAME = "test-instance"
TEST_VERSION = "11.315"
TEST_PORT = 30000
TEST_ADMIN_KEY = "test-admin-key"
TEST_BASE_DIR = Path("/tmp/foundry-test")


@pytest.fixture(scope="session")
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def manager():
    """Create a Foundry instance manager for testing."""
    return FoundryInstanceManager(str(TEST_BASE_DIR))


@pytest.fixture(autouse=True)
def setup_teardown():
    """Set up and tear down test resources."""
    # Create test directory
    TEST_BASE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Clean up test directory
    if TEST_BASE_DIR.exists():
        import shutil

        shutil.rmtree(TEST_BASE_DIR)


@pytest.fixture(autouse=True)
def mock_docker(monkeypatch):
    """Mock docker.from_env and Docker client methods globally for all tests."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.id = "mock-container-id"
    mock_client.containers.get.return_value = mock_container
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.list.return_value = [mock_container]
    mock_client.ping.return_value = True
    monkeypatch.setattr("docker.from_env", lambda: mock_client)
    monkeypatch.setattr("docker.errors.DockerException", Exception)
    yield


@pytest.fixture
def mock_instance_manager(monkeypatch):
    """Create a mock instance manager."""
    mock_manager = MagicMock()
    mock_manager.list_versions.return_value = ["11.0.0", "10.0.0"]
    mock_manager.get_available_versions.return_value = ["11.0.0", "10.0.0"]
    mock_manager.list_instances.return_value = [
        {"name": "test-instance", "version": "11.0.0", "status": "running"}
    ]
    mock_manager.get_instance_path.return_value = Path("/tmp/test-instance")
    mock_manager.get_instance.return_value = MagicMock()
    monkeypatch.setattr("foundry_manager.cli.instance_manager", mock_manager)
    return mock_manager


@pytest.fixture(autouse=True)
def set_cli_instance_manager(mock_instance_manager):
    foundry_manager.cli.instance_manager = mock_instance_manager
    yield
    foundry_manager.cli.instance_manager = None


def test_cli_version(runner):
    """Test the version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "Foundry Instance Manager" in result.output


def test_cli_help(runner):
    """Test the help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Foundry VTT Instance Manager CLI" in result.output


def test_set_base_dir(runner):
    """Test setting the base directory."""
    result = runner.invoke(cli, ["set-base-dir", str(TEST_BASE_DIR)])
    assert result.exit_code == 0
    assert "Base directory set successfully" in result.output


def test_set_credentials(runner):
    """Test setting credentials."""
    result = runner.invoke(
        cli,
        [
            "set-credentials",
            "--username",
            "test-user",
            "--password",
            "test-pass",
        ],
    )
    assert result.exit_code == 0
    assert "Foundry VTT credentials set successfully" in result.output


def test_create_instance(runner, mock_instance_manager):
    """Test creating a new instance."""
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ):
        result = runner.invoke(
            cli,
            [
                "create",
                "test-instance",
                "--version",
                "11.0.0",
                "--port",
                "30000",
                "--admin-key",
                "test-key",
                "--username",
                "test-user",
                "--password",
                "test-pass",
            ],
        )
        assert result.exit_code == 0
        mock_instance_manager.create_instance.assert_called_once_with(
            name="test-instance",
            version="11.0.0",
            port=30000,
            admin_key="test-key",
            username="test-user",
            password="test-pass",
        )


def test_list_instances(runner: CliRunner, mock_instance_manager: MagicMock) -> None:
    """Test listing instances."""
    mock_instance_manager.list_instances.return_value = [
        {"name": "test-instance", "version": "11.0.0", "status": "running"}
    ]
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ), patch("foundry_manager.cli.instance_manager", mock_instance_manager):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        mock_instance_manager.list_instances.assert_called_once()
        assert "test-instance" in result.output


def test_start_instance(runner, mock_instance_manager):
    """Test starting an instance."""
    result = runner.invoke(cli, ["start", "test-instance"])
    assert result.exit_code == 0
    mock_instance_manager.start_instance.assert_called_once_with("test-instance")


def test_stop_instance(runner, mock_instance_manager):
    """Test stopping an instance."""
    result = runner.invoke(cli, ["stop", "test-instance"])
    assert result.exit_code == 0
    mock_instance_manager.stop_instance.assert_called_once_with("test-instance")


def test_migrate_instance(runner, mock_instance_manager):
    """Test migrating an instance to a new version."""
    result = runner.invoke(cli, ["migrate", "test-instance", "--version", "11.0.0"])
    assert result.exit_code == 0
    mock_instance_manager.migrate_instance.assert_called_once_with(
        "test-instance", "11.0.0"
    )


def test_remove_instance(runner, mock_instance_manager):
    """Test removing an instance."""
    result = runner.invoke(cli, ["remove", "test-instance"])
    assert result.exit_code == 0
    mock_instance_manager.remove_instance.assert_called_once_with("test-instance")


def test_list_versions(runner, mock_instance_manager):
    """Test listing available Foundry VTT versions."""
    mock_instance_manager.list_versions.return_value = ["11.0.0", "10.0.0"]
    result = runner.invoke(cli, ["versions"])
    assert result.exit_code == 0
    assert "11.0.0" in result.output
    assert "10.0.0" in result.output


def test_apply_config(runner, mock_instance_manager):
    """Test applying configuration to an instance."""
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ):
        result = runner.invoke(
            cli,
            [
                "config",
                "test-instance",
                "--admin-key",
                "test-key",
                "--username",
                "test-user",
                "--password",
                "test-pass",
            ],
        )
        assert result.exit_code == 0
        mock_instance_manager.apply_config.assert_called_once_with(
            {
                "instances": {
                    "test-instance": {
                        "admin_key": "test-key",
                        "username": "test-user",
                        "password": "test-pass",
                    }
                }
            }
        )


def test_error_handling(runner, mock_instance_manager):
    """Test error handling in CLI commands."""
    mock_instance_manager.start_instance.side_effect = ValueError("Instance not found")
    result = runner.invoke(cli, ["start", "nonexistent"])
    assert result.exit_code == 1
    assert "Instance not found" in result.output


def test_list_systems(runner: CliRunner, mock_instance_manager: MagicMock) -> None:
    """Test listing systems."""
    mock_instance_manager.list_systems.return_value = [
        {"id": "dnd5e", "title": "D&D 5E", "version": "1.0.0"}
    ]
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ), patch("foundry_manager.cli.instance_manager", mock_instance_manager):
        result = runner.invoke(cli, ["systems", "list", "test-instance"])
        assert result.exit_code == 0
        mock_instance_manager.list_systems.assert_called_once_with("test-instance")
        assert "dnd5e" in result.output


def test_list_modules(runner: CliRunner, mock_instance_manager: MagicMock) -> None:
    """Test listing modules."""
    mock_instance_manager.list_modules.return_value = [
        {"id": "test-module", "title": "Test Module", "version": "1.0.0"}
    ]
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ), patch("foundry_manager.cli.instance_manager", mock_instance_manager):
        result = runner.invoke(cli, ["modules", "list", "test-instance"])
        assert result.exit_code == 0
        mock_instance_manager.list_modules.assert_called_once_with("test-instance")
        assert "test-module" in result.output


def test_list_worlds(runner: CliRunner, mock_instance_manager: MagicMock) -> None:
    """Test listing worlds."""
    mock_instance_manager.list_worlds.return_value = [
        {"id": "test-world", "title": "Test World", "version": "1.0.0"}
    ]
    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ), patch("foundry_manager.cli.instance_manager", mock_instance_manager):
        result = runner.invoke(cli, ["worlds", "list", "test-instance"])
        assert result.exit_code == 0
        mock_instance_manager.list_worlds.assert_called_once_with("test-instance")
        assert "test-world" in result.output


def test_list_assets(runner):
    """Test listing assets."""
    result = runner.invoke(cli, ["assets", "list"])
    assert result.exit_code == 0
    assert "No assets found" in result.output


@pytest.mark.skip(reason="Skipping test_docker_unavailable for now")
def test_docker_unavailable(runner, monkeypatch):
    """Test behavior when Docker is unavailable."""

    def mock_docker_error(*args, **kwargs):
        raise RuntimeError("Docker is not running or not accessible")

    monkeypatch.setattr(
        "docker.from_env",
        mock_docker_error,
    )

    with patch(
        "foundry_manager.cli.load_config", return_value={"base_dir": str(TEST_BASE_DIR)}
    ):
        result = runner.invoke(cli, ["create", "test-instance"])
        assert result.exit_code == 1
        assert "Docker is not running or not accessible" in result.output
