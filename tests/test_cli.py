"""Tests for the CLI interface."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from foundry_manager.cli import cli

# Test data
TEST_CONFIG = {
    "base_dir": "/test/base",
    "username": "test_user",
    "password": "test_pass",
}
TEST_BASE_DIR = Path("/test/base")


class TestInstanceCommands:
    """Test suite for instance management commands."""

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
                ],
            )
            assert result.exit_code == 0
            assert "✓ Created instance test-instance (v11.0.0)" in result.output
            mock_instance_manager.create_instance.assert_called_once_with(
                name="test-instance",
                version="11.0.0",
                port=30000,
                admin_key="test-key",
                username="test_user",
                password="test_pass",
            )

    def test_start_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test starting an instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG):
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
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG):
            result = runner.invoke(cli, ["stop", "test-instance"])
            assert result.exit_code == 0
            assert "Instance test-instance stopped successfully" in result.output
            mock_instance_manager.stop_instance.assert_called_once_with("test-instance")

    def test_remove_instance(self, runner, mock_instance_manager, mock_config_dir):
        """Test removing an instance."""
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG):
            result = runner.invoke(cli, ["remove", "test-instance"])
            assert result.exit_code == 0
            assert "Instance test-instance removed successfully" in result.output
            mock_instance_manager.remove_instance.assert_called_once_with(
                "test-instance"
            )


class TestListCommands:
    """Test suite for list commands."""

    def test_list_instances(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing instances."""
        mock_instance_manager.list_instances.return_value = [
            {"name": "test-instance", "version": "11.0.0", "status": "running"}
        ]
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.instance_manager", mock_instance_manager
        ):
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            mock_instance_manager.list_instances.assert_called_once()
            assert "test-instance" in result.output

    def test_list_systems(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing systems."""
        mock_instance_manager.list_systems.return_value = [
            {"id": "dnd5e", "title": "D&D 5E", "version": "1.0.0"}
        ]
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.instance_manager", mock_instance_manager
        ):
            result = runner.invoke(cli, ["systems", "list", "test-instance"])
            assert result.exit_code == 0
            mock_instance_manager.list_systems.assert_called_once_with("test-instance")
            assert "dnd5e" in result.output

    def test_list_modules(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing modules."""
        mock_instance_manager.list_modules.return_value = [
            {"id": "test-module", "title": "Test Module", "version": "1.0.0"}
        ]
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.instance_manager", mock_instance_manager
        ):
            result = runner.invoke(cli, ["modules", "list", "test-instance"])
            assert result.exit_code == 0
            mock_instance_manager.list_modules.assert_called_once_with("test-instance")
            assert "test-module" in result.output

    def test_list_worlds(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing worlds."""
        mock_instance_manager.list_worlds.return_value = [
            {"id": "test-world", "title": "Test World", "version": "1.0.0"}
        ]
        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG), patch(
            "foundry_manager.cli.instance_manager", mock_instance_manager
        ):
            result = runner.invoke(cli, ["worlds", "list", "test-instance"])
            assert result.exit_code == 0
            mock_instance_manager.list_worlds.assert_called_once_with("test-instance")
            assert "test-world" in result.output

    def test_list_versions(self, runner, mock_instance_manager, mock_config_dir):
        """Test listing available versions."""
        mock_versions = ["11.0.0", "11.1.0", "11.2.0"]
        mock_instance_manager.list_versions.return_value = mock_versions
        mock_instance_manager.get_available_versions.return_value = mock_versions

        with patch(
            "foundry_manager.cli.Path.home", return_value=mock_config_dir.parent
        ), patch("foundry_manager.cli.load_config", return_value=TEST_CONFIG):
            result = runner.invoke(cli, ["versions"])
            assert result.exit_code == 0
            for v in mock_versions:
                assert v in result.output


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_instance_manager():
    """Create a mock instance manager."""
    with patch("foundry_manager.cli.FoundryInstanceManager") as mock:
        manager = mock.return_value
        yield manager


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create a mock config directory."""
    config_dir = tmp_path / ".fim"
    config_dir.mkdir()
    return config_dir


@pytest.fixture(autouse=True)
def set_cli_instance_manager(mock_instance_manager):
    import foundry_manager.cli

    foundry_manager.cli.instance_manager = mock_instance_manager
    yield
    foundry_manager.cli.instance_manager = None
