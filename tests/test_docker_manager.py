"""Tests for the Docker manager functionality."""

from unittest.mock import MagicMock, patch

import pytest

from foundry_manager.docker_manager import ContainerNotFoundError, DockerManager


@pytest.fixture
def base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return tmp_path


@pytest.fixture
def mock_docker_client():
    """Create a mock docker client."""
    with patch("docker.from_env") as mock:
        client = mock.return_value
        yield client


@pytest.fixture
def docker_manager(base_dir, mock_docker_client):
    """Create a docker manager with mocked client."""
    return DockerManager(base_dir=base_dir)


class TestContainerCreation:
    """Test suite for container creation functionality.

    This class contains tests for the container creation functionality of the
    DockerManager. It tests both successful container creation scenarios and error
    cases.

    The tests cover:
    - Creating a container with all parameters (including proxy port)
    - Creating a container without proxy port
    - Error handling for container creation failures
    - Validation of container configuration
    """

    def test_create_container_success(self, docker_manager, mock_docker_client):
        """Test successful container creation."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "created"
        mock_docker_client.containers.run.return_value = mock_container

        # Create container
        container = docker_manager.create_container(
            name="test-container",
            image="test-image:latest",
            volumes={"/host/path": {"bind": "/container/path", "mode": "rw"}},
            environment={"TEST_VAR": "test_value"},
            port=30000,
            proxy_port=443,
        )

        # Verify container
        assert container == mock_container
        assert container.id == "test-container-id"
        assert container.status == "created"

        # Verify docker client calls
        mock_docker_client.containers.run.assert_called_once()
        call_args = mock_docker_client.containers.run.call_args[1]
        assert call_args["name"] == "test-container"
        assert call_args["image"] == "test-image:latest"
        assert call_args["detach"] is True
        assert call_args["ports"] == {"30000/tcp": 30000, "443/tcp": 443}

    def test_create_container_without_proxy(self, docker_manager, mock_docker_client):
        """Test container creation without proxy port."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "created"
        mock_docker_client.containers.run.return_value = mock_container

        # Create container
        container = docker_manager.create_container(
            name="test-container",
            image="test-image:latest",
            volumes={"/host/path": {"bind": "/container/path", "mode": "rw"}},
            environment={"TEST_VAR": "test_value"},
            port=30000,
        )

        # Verify container
        assert container == mock_container
        assert container.id == "test-container-id"
        assert container.status == "created"

        # Verify docker client calls
        mock_docker_client.containers.run.assert_called_once()
        call_args = mock_docker_client.containers.run.call_args[1]
        assert call_args["name"] == "test-container"
        assert call_args["image"] == "test-image:latest"
        assert call_args["detach"] is True
        assert call_args["ports"] == {"30000/tcp": 30000}


class TestContainerManagement:
    """Test suite for container management functionality.

    This class contains tests for the container management functionality of the
    DockerManager. It tests both successful container retrieval scenarios and error
    cases.

    The tests cover:
    - Getting an existing container
    - Getting a non-existent container
    - Starting a container
    - Stopping a container
    - Removing a container
    """

    def test_get_container_success(self, docker_manager, mock_docker_client):
        """Test getting an existing container."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "running"
        mock_docker_client.containers.get.return_value = mock_container

        # Get container
        container = docker_manager.get_container("test-container")

        # Verify container
        assert container == mock_container
        assert container.id == "test-container-id"
        assert container.status == "running"

        # Verify docker client calls
        mock_docker_client.containers.get.assert_called_once_with("test-container")

    def test_get_container_not_found(self, docker_manager, mock_docker_client):
        """Test getting a non-existent container."""
        # Mock container not found
        mock_docker_client.containers.get.side_effect = Exception("Container not found")

        # Attempt to get container
        with pytest.raises(ContainerNotFoundError) as exc_info:
            docker_manager.get_container("nonexistent-container")
        assert str(exc_info.value) == "Container 'nonexistent-container' not found"

    def test_start_container_success(self, docker_manager, mock_docker_client):
        """Test starting a container."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "created"
        mock_docker_client.containers.get.return_value = mock_container

        # Start container
        docker_manager.start_container("test-container")

        # Verify docker client calls
        mock_docker_client.containers.get.assert_called_once_with("test-container")
        mock_container.start.assert_called_once()

    def test_stop_container_success(self, docker_manager, mock_docker_client):
        """Test stopping a container."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "running"
        mock_docker_client.containers.get.return_value = mock_container

        # Stop container
        docker_manager.stop_container("test-container")

        # Verify docker client calls
        mock_docker_client.containers.get.assert_called_once_with("test-container")
        mock_container.stop.assert_called_once()

    def test_remove_container_success(self, docker_manager, mock_docker_client):
        """Test removing a container."""
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_container.status = "exited"
        mock_docker_client.containers.get.return_value = mock_container

        # Remove container
        docker_manager.remove_container("test-container")

        # Verify docker client calls
        mock_docker_client.containers.get.assert_called_once_with("test-container")
        mock_container.remove.assert_called_once()


class TestErrorHandling:
    """Test suite for error handling functionality.

    This class contains tests for the error handling functionality of the
    DockerManager. It tests both successful error handling scenarios and error
    cases.

    The tests cover:
    - Starting a non-existent container
    - Stopping a non-existent container
    - Removing a non-existent container
    - Container creation failures
    """

    def test_start_nonexistent_container(self, docker_manager, mock_docker_client):
        """Test starting a non-existent container."""
        # Mock container not found
        mock_docker_client.containers.get.side_effect = Exception("Container not found")

        # Attempt to start container
        with pytest.raises(ContainerNotFoundError) as exc_info:
            docker_manager.start_container("nonexistent-container")
        assert str(exc_info.value) == "Container 'nonexistent-container' not found"

    def test_stop_nonexistent_container(self, docker_manager, mock_docker_client):
        """Test stopping a non-existent container."""
        # Mock container not found
        mock_docker_client.containers.get.side_effect = Exception("Container not found")

        # Attempt to stop container
        with pytest.raises(ContainerNotFoundError) as exc_info:
            docker_manager.stop_container("nonexistent-container")
        assert str(exc_info.value) == "Container 'nonexistent-container' not found"

    def test_remove_nonexistent_container(self, docker_manager, mock_docker_client):
        """Test removing a non-existent container."""
        # Mock container not found
        mock_docker_client.containers.get.side_effect = Exception("Container not found")

        # Attempt to remove container
        with pytest.raises(ContainerNotFoundError) as exc_info:
            docker_manager.remove_container("nonexistent-container")
        assert str(exc_info.value) == "Container 'nonexistent-container' not found"

    def test_create_container_failure(self, docker_manager, mock_docker_client):
        """Test container creation failure."""
        # Mock container creation failure
        mock_docker_client.containers.run.side_effect = Exception(
            "Failed to create container"
        )

        # Attempt to create container
        with pytest.raises(Exception) as exc_info:
            docker_manager.create_container(
                name="test-container", image="test-image:latest", port=30000
            )
        assert (
            str(exc_info.value)
            == "Failed to create container: Failed to create container"
        )
