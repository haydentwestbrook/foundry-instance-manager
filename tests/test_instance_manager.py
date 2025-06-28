"""Tests for the Foundry instance manager functionality."""

from unittest.mock import MagicMock

import docker
import pytest

from foundry_manager.foundry_instance_manager import FoundryInstanceManager


@pytest.fixture
def base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return tmp_path


@pytest.fixture
def mock_docker(monkeypatch):
    """Mock Docker client."""
    mock_docker = MagicMock()
    monkeypatch.setattr("docker.from_env", lambda: mock_docker)
    return mock_docker


@pytest.fixture
def instance_manager(tmp_path, mock_docker):
    """Create a FoundryInstanceManager instance for testing with mocked Docker."""
    return FoundryInstanceManager(base_dir=tmp_path, docker_client=mock_docker)


class TestInstanceCreation:
    """Test suite for instance creation functionality."""

    def test_create_instance_success(self, instance_manager, mock_docker):
        """Test successful instance creation."""
        # Mock container
        mock_container = MagicMock()
        mock_container.name = "foundry-test-instance"
        mock_container.status = "created"
        mock_docker.containers.run.return_value = mock_container
        mock_docker.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )
        mock_docker.images.pull.return_value = MagicMock()

        # Create instance
        instance_manager.create_instance(
            name="test-instance",
            version="11.0.0",
            port=30000,
            admin_key="test-key",
            username="test-user",
            password="test-pass",
        )

        # Verify container was created
        mock_docker.containers.run.assert_called_once_with(
            "felddy/foundryvtt:11.0.0",
            name="foundry-test-instance",
            detach=True,
            ports={"30000/tcp": 30000},
            volumes={
                str(instance_manager._get_instance_path("test-instance").resolve()): {
                    "bind": "/data",
                    "mode": "rw",
                }
            },
            environment={
                "FOUNDRY_USERNAME": "test-user",
                "FOUNDRY_PASSWORD": "test-pass",
                "FOUNDRY_ADMIN_KEY": "test-key",
            },
        )

    def test_create_instance_existing(self, instance_manager, mock_docker):
        """Test creating an instance that already exists."""
        # Create instance config
        instance_path = instance_manager._get_instance_path("test-instance")
        instance_path.mkdir(parents=True, exist_ok=True)
        config = {
            "name": "test-instance",
            "version": "11.0.0",
            "port": 30000,
            "data_dir": str(instance_path),
            "status": "created",
            "admin_key": "test-key",
            "username": "test-user",
            "password": "test-pass",
        }
        instance_manager._save_instance_config("test-instance", config)

        # Try to create instance again
        with pytest.raises(ValueError, match="Instance test-instance already exists"):
            instance_manager.create_instance(
                name="test-instance",
                version="11.0.0",
                port=30000,
                admin_key="test-key",
                username="test-user",
                password="test-pass",
            )

    def test_create_instance_cleanup_on_error(self, instance_manager, mock_docker):
        """Test cleanup when instance creation fails."""
        # Mock container creation failure
        mock_docker.containers.run.side_effect = Exception("Failed to create container")

        # Try to create instance
        with pytest.raises(
            RuntimeError, match="Failed to create instance test-instance"
        ):
            instance_manager.create_instance(
                name="test-instance",
                version="11.0.0",
                port=30000,
                admin_key="test-key",
                username="test-user",
                password="test-pass",
            )

        # Verify cleanup
        instance_path = instance_manager._get_instance_path("test-instance")
        assert not instance_path.exists()


class TestInstanceManagement:
    """Test suite for instance management functionality."""

    def test_list_instances(self, instance_manager, mock_docker):
        """Test listing all instances."""
        # Mock container
        mock_container = MagicMock()
        mock_container.name = "foundry-test-instance"
        mock_container.status = "running"
        mock_docker.containers.get.return_value = mock_container

        # Create instance config
        instance_path = instance_manager._get_instance_path("test-instance")
        instance_path.mkdir(parents=True, exist_ok=True)
        config = {
            "name": "test-instance",
            "version": "11.0.0",
            "port": 30000,
            "data_dir": str(instance_path),
            "status": "running",
            "admin_key": "test-key",
            "username": "test-user",
            "password": "test-pass",
        }
        instance_manager._save_instance_config("test-instance", config)

        # List instances
        instances = instance_manager.list_instances()
        assert len(instances) == 1
        assert instances[0]["name"] == "test-instance"
        assert instances[0]["version"] == "11.0.0"
        assert instances[0]["status"] == "running"

    def test_start_instance(self, instance_manager, mock_docker):
        """Test starting an instance."""
        # Mock container
        mock_container = MagicMock()
        mock_container.name = "foundry-test-instance"
        mock_container.status = "stopped"
        mock_docker.containers.get.return_value = mock_container

        # Create instance config
        instance_path = instance_manager._get_instance_path("test-instance")
        instance_path.mkdir(parents=True, exist_ok=True)
        config = {
            "name": "test-instance",
            "version": "11.0.0",
            "port": 30000,
            "data_dir": str(instance_path),
            "status": "stopped",
            "admin_key": "test-key",
            "username": "test-user",
            "password": "test-pass",
        }
        instance_manager._save_instance_config("test-instance", config)

        # Start instance
        instance_manager.start_instance("test-instance")
        mock_container.start.assert_called_once()

    def test_stop_instance(self, instance_manager, mock_docker):
        """Test stopping an instance."""
        # Mock container
        mock_container = MagicMock()
        mock_container.name = "foundry-test-instance"
        mock_container.status = "running"
        mock_docker.containers.get.return_value = mock_container

        # Create instance config
        instance_path = instance_manager._get_instance_path("test-instance")
        instance_path.mkdir(parents=True, exist_ok=True)
        config = {
            "name": "test-instance",
            "version": "11.0.0",
            "port": 30000,
            "data_dir": str(instance_path),
            "status": "running",
            "admin_key": "test-key",
            "username": "test-user",
            "password": "test-pass",
        }
        instance_manager._save_instance_config("test-instance", config)

        # Stop instance
        instance_manager.stop_instance("test-instance")
        mock_container.stop.assert_called_once()

    def test_remove_instance(self, instance_manager, mock_docker):
        """Test removing an instance."""
        # Mock container
        mock_container = MagicMock()
        mock_container.name = "foundry-test-instance"
        mock_docker.containers.get.return_value = mock_container

        # Create instance config
        instance_path = instance_manager._get_instance_path("test-instance")
        instance_path.mkdir(parents=True, exist_ok=True)
        config = {
            "name": "test-instance",
            "version": "11.0.0",
            "port": 30000,
            "data_dir": str(instance_path),
            "status": "stopped",
            "admin_key": "test-key",
            "username": "test-user",
            "password": "test-pass",
        }
        instance_manager._save_instance_config("test-instance", config)

        # Remove instance
        instance_manager.remove_instance("test-instance")
        mock_container.remove.assert_called_once_with(force=True)
        assert not instance_path.exists()


class TestErrorHandling:
    """Test error handling functionality."""

    def test_get_nonexistent_instance(self, instance_manager, mock_docker):
        """Test getting a non-existent instance."""
        mock_docker.containers.get.side_effect = Exception("Container not found")
        with pytest.raises(FileNotFoundError):
            instance_manager.get_instance_status("nonexistent")

    def test_start_nonexistent_instance(self, instance_manager, mock_docker):
        """Test starting a non-existent instance."""
        mock_docker.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )
        with pytest.raises(ValueError, match="Instance test-instance not found"):
            instance_manager.start_instance("test-instance")

    def test_stop_nonexistent_instance(self, instance_manager, mock_docker):
        """Test stopping a non-existent instance."""
        mock_docker.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )
        with pytest.raises(ValueError, match="Instance test-instance not found"):
            instance_manager.stop_instance("test-instance")

    def test_remove_nonexistent_instance(self, instance_manager, mock_docker):
        """Test removing a non-existent instance."""
        mock_docker.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )
        with pytest.raises(ValueError, match="Instance test-instance not found"):
            instance_manager.remove_instance("test-instance")
