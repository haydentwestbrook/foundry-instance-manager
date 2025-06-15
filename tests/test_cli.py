"""Tests for the CLI interface of Foundry Instance Manager."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from foundry_manager.cli import cli
from foundry_manager.foundry_instance_manager import FoundryInstance  # noqa: E501

# Test data
TEST_CONFIG = {
    "base_dir": "/test/base/dir",
    "foundry_username": "test_user",
    "foundry_password": "test_pass",
}


@pytest.fixture
def runner():
    """Create a CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".fim"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_config_file(mock_config_dir):
    """Create a temporary config file for testing."""
    config_file = mock_config_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(TEST_CONFIG, f)
    return config_file


@pytest.fixture
def mock_instance_manager():
    """Create a mock instance manager."""
    with patch("foundry_manager.cli.FoundryInstanceManager") as mock:
        manager = mock.return_value
        yield manager


class TestConfigCommands:
    """Test configuration-related CLI commands."""

    def test_set_base_dir(self, runner, mock_config_dir):
        """Test setting the base directory."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["set-base-dir", "--base-dir", "/new/base/dir"])
            assert result.exit_code == 0
            assert "Base directory set successfully" in result.output

    def test_set_credentials(self, runner, mock_config_dir):
        """Test setting Foundry VTT credentials."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(
                cli,
                [
                    "set-credentials",
                    "--username",
                    "test_user",
                    "--password",
                    "test_pass",
                ],
            )
            assert result.exit_code == 0
            assert "Foundry VTT credentials set successfully" in result.output


class TestInstanceCommands:
    """Test instance-related CLI commands."""

    def test_create_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test creating a new instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG):
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
                    "--environment",
                    "TEST_VAR=test_value",
                ],
            )
            assert result.exit_code == 0
            assert "Instance test-instance created successfully" in result.output
            mock_instance_manager.create_instance.assert_called_once()

    def test_start_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test starting an instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["start", "test-instance"])
            assert result.exit_code == 0
            assert "Instance test-instance started successfully" in result.output
            mock_instance_manager.start_instance.assert_called_once_with(
                "test-instance"
            )

    def test_stop_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test stopping an instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["stop", "test-instance"])
            assert result.exit_code == 0
            assert "Instance test-instance stopped successfully" in result.output
            mock_instance_manager.stop_instance.assert_called_once_with("test-instance")

    def test_remove_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test removing an instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["remove", "test-instance"], input="y\n")
            assert result.exit_code == 0
            assert "Instance test-instance removed successfully" in result.output
            mock_instance_manager.remove_instance.assert_called_once_with(
                "test-instance"
            )

    def test_migrate_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test migrating an instance to a new version."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["migrate", "test-instance", "11.1.0"])
            assert result.exit_code == 0
            assert (
                "Instance test-instance migrated to version 11.1.0 successfully"
                in result.output
            )
            mock_instance_manager.migrate_instance.assert_called_once_with(
                "test-instance", "11.1.0"
            )


class TestListCommands:
    """Test suite for list-related CLI commands.

    This class contains tests for commands that list information about Foundry VTT
    instances and available versions. It tests both the successful execution of
    these commands and verifies that the correct data is displayed in the output.

    The tests cover:
    - Listing all Foundry VTT instances with their details
    - Listing available Foundry VTT versions
    """

    def test_list_instances(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing all instances."""
        # Mock instance data
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.status = "running"
        mock_instance.port = 30000
        mock_instance.version = "11.0.0"
        mock_instance.data_dir = Path("/test/data")
        mock_instance_manager.list_instances.return_value = [mock_instance]

        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.FoundryInstanceManager",
            return_value=mock_instance_manager,
        ):
            result = runner.invoke(cli, ["list-instances"])
            if result.exit_code != 0:
                print("\n--- CLI OUTPUT ---\n", result.output)
                print("\n--- CLI EXCEPTION ---\n", result.exception)
            assert result.exit_code == 0
            assert "test-instance" in result.output
            assert "running" in result.output
            mock_instance_manager.list_instances.assert_called_once()

    def test_list_versions(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing available versions."""
        mock_versions = [
            {"version": "11.0.0", "created": "2023-01-01"},
            {"version": "11.1.0", "created": "2023-02-01"},
        ]
        mock_instance_manager.get_available_versions.return_value = mock_versions

        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["versions"])
            assert result.exit_code == 0
            assert "11.0.0" in result.output
            assert "11.1.0" in result.output
            mock_instance_manager.get_available_versions.assert_called_once()


class TestErrorHandling:
    """Test suite for error handling in CLI commands.

    This class contains tests for error scenarios that should be handled gracefully
    by the CLI. It tests:
    - Creating an instance without credentials
    - Removing a non-existent instance
    - Migrating a non-existent instance
    """

    def test_create_instance_without_credentials(self, runner, mock_config_dir):
        """Test creating an instance without credentials."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch(
            "foundry_manager.cli.load_config", return_value={"base_dir": "/test/dir"}
        ):
            result = runner.invoke(cli, ["create", "test-instance"])
            assert result.exit_code != 0
            assert "Foundry VTT credentials not set" in result.output

    def test_remove_nonexistent_instance(
        self, runner, mock_instance_manager, mock_config_dir
    ):
        """Test removing a non-existent instance."""
        mock_instance_manager.get_instance.return_value = None
        mock_instance_manager.remove_instance.side_effect = ValueError(
            "Instance nonexistent-instance not found"
        )

        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["remove", "nonexistent-instance"], input="y\n")
            assert result.exit_code != 0
            assert "Instance nonexistent-instance not found" in result.output

    def test_migrate_nonexistent_instance(
        self, runner, mock_instance_manager, mock_config_dir
    ):
        """Test migrating a non-existent instance."""
        mock_instance_manager.get_instance.return_value = None
        mock_instance_manager.migrate_instance.side_effect = ValueError(
            "Instance nonexistent-instance not found"
        )

        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ):
            result = runner.invoke(cli, ["migrate", "nonexistent-instance", "11.1.0"])
            assert result.exit_code != 0
            assert "Instance nonexistent-instance not found" in result.output


class TestSystemCommands:
    """Test system management CLI commands."""

    @pytest.fixture
    def mock_system_manager(self):
        """Create a mock GameSystemManager for testing."""
        with patch("foundry_manager.cli.GameSystemManager") as mock:
            manager = mock.return_value
            yield manager

    def test_systems_list(
        self, runner, mock_instance_manager, mock_system_manager, mock_config_dir
    ):
        """Test listing installed game systems for an instance."""
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.data_dir = Path("/test/data")
        mock_instance_manager.get_instance.return_value = mock_instance
        mock_system_manager.list_systems.return_value = [
            {"id": "dnd5e", "title": "D&D 5E", "version": "5.0.3"},
            {"id": "pf2e", "title": "Pathfinder 2E", "version": "7.2.0"},
        ]
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.GameSystemManager", return_value=mock_system_manager
        ), patch(
            "foundry_manager.cli.FoundryInstanceManager",
            return_value=mock_instance_manager,
        ):
            result = runner.invoke(cli, ["systems", "list-systems", "test-instance"])
            assert result.exit_code == 0
            assert "D&D 5E" in result.output
            assert "Pathfinder 2E" in result.output
            mock_system_manager.list_systems.assert_called_once_with(mock_instance)

    def test_systems_install(
        self, runner, mock_instance_manager, mock_system_manager, mock_config_dir
    ):
        """Test installing a game system from a URL."""
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.data_dir = Path("/test/data")
        mock_instance_manager.get_instance.return_value = mock_instance
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.GameSystemManager", return_value=mock_system_manager
        ), patch(
            "foundry_manager.cli.FoundryInstanceManager",
            return_value=mock_instance_manager,
        ):
            result = runner.invoke(
                cli,
                [
                    "systems",
                    "install-system",
                    "test-instance",
                    "https://example.com/system.zip",
                ],
            )
            assert result.exit_code == 0
            mock_system_manager.install_system.assert_called_once_with(
                mock_instance, "https://example.com/system.zip"
            )

    def test_systems_remove(
        self, runner, mock_instance_manager, mock_system_manager, mock_config_dir
    ):
        """Test removing a game system from an instance."""
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.data_dir = Path("/test/data")
        mock_instance_manager.get_instance.return_value = mock_instance
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.GameSystemManager", return_value=mock_system_manager
        ), patch(
            "foundry_manager.cli.FoundryInstanceManager",
            return_value=mock_instance_manager,
        ):
            result = runner.invoke(
                cli, ["systems", "remove-system", "test-instance", "dnd5e"]
            )
            assert result.exit_code == 0
            mock_system_manager.remove_system.assert_called_once_with(
                mock_instance, "dnd5e"
            )
