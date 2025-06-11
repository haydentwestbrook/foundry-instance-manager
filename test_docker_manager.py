import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from foundry_manager.docker_manager import DockerManager

@pytest.fixture
def mock_docker_client(mocker):
    """Fixture to create a mock Docker client."""
    mock_client = MagicMock()
    mocker.patch('docker.from_env', return_value=mock_client)
    return mock_client

@pytest.fixture
def mock_requests(mocker):
    """Fixture to mock requests for version checking."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'results': [
            {'name': '11.315', 'last_updated': '2024-01-01T00:00:00Z'},
            {'name': '11.316', 'last_updated': '2024-01-02T00:00:00Z'},
            {'name': 'latest', 'last_updated': '2024-01-03T00:00:00Z'}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch('requests.get', return_value=mock_response)
    return mock_response

@pytest.fixture
def docker_manager(mock_docker_client, tmp_path):
    """Fixture to create a DockerManager instance with a temporary directory."""
    with patch('pathlib.Path.cwd', return_value=tmp_path):
        manager = DockerManager()
        return manager

def test_init_creates_directories(docker_manager, tmp_path):
    """Test that initialization creates necessary directories."""
    shared_dir = tmp_path / "data" / "shared"
    containers_dir = tmp_path / "data" / "containers"
    
    assert shared_dir.exists()
    assert containers_dir.exists()

def test_create_container_success(docker_manager, mock_docker_client):
    """Test successful container creation."""
    name = "test-container"
    image = "test-image"
    
    # Mock container creation
    mock_container = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container
    
    container = docker_manager.create_container(name, image)
    
    # Verify container was created with correct parameters
    mock_docker_client.containers.create.assert_called_once()
    call_args = mock_docker_client.containers.create.call_args[1]
    assert call_args['image'] == image
    assert call_args['name'] == name
    assert call_args['detach'] is True
    
    # Verify volume mounts
    volumes = call_args['volumes']
    assert len(volumes) == 2
    assert '/data/container' in [v['bind'] for v in volumes.values()]
    assert '/data/shared' in [v['bind'] for v in volumes.values()]

def test_create_container_image_not_found(docker_manager, mock_docker_client):
    """Test container creation with non-existent image."""
    mock_docker_client.containers.create.side_effect = Exception("Image not found")
    
    with pytest.raises(Exception):
        docker_manager.create_container("test-container", "non-existent-image")

def test_list_containers(docker_manager, mock_docker_client):
    """Test listing containers."""
    # Create mock containers
    mock_container1 = MagicMock()
    mock_container1.name = "container1"
    mock_container1.status = "running"
    mock_container1.image.tags = ["image1:latest"]
    
    mock_container2 = MagicMock()
    mock_container2.name = "container2"
    mock_container2.status = "stopped"
    mock_container2.image.tags = ["image2:latest"]
    
    mock_docker_client.containers.list.return_value = [mock_container1, mock_container2]
    
    # Call list_containers
    docker_manager.list_containers()
    
    # Verify containers were listed
    mock_docker_client.containers.list.assert_called_once_with(all=True)

def test_start_container_success(docker_manager, mock_docker_client):
    """Test successful container start."""
    name = "test-container"
    mock_container = MagicMock()
    mock_docker_client.containers.get.return_value = mock_container
    
    docker_manager.start_container(name)
    
    mock_docker_client.containers.get.assert_called_once_with(name)
    mock_container.start.assert_called_once()

def test_start_container_not_found(docker_manager, mock_docker_client):
    """Test starting non-existent container."""
    mock_docker_client.containers.get.side_effect = Exception("Container not found")
    
    with pytest.raises(Exception):
        docker_manager.start_container("non-existent-container")

def test_stop_container_success(docker_manager, mock_docker_client):
    """Test successful container stop."""
    name = "test-container"
    mock_container = MagicMock()
    mock_docker_client.containers.get.return_value = mock_container
    
    docker_manager.stop_container(name)
    
    mock_docker_client.containers.get.assert_called_once_with(name)
    mock_container.stop.assert_called_once()

def test_stop_container_not_found(docker_manager, mock_docker_client):
    """Test stopping non-existent container."""
    mock_docker_client.containers.get.side_effect = Exception("Container not found")
    
    with pytest.raises(Exception):
        docker_manager.stop_container("non-existent-container")

def test_remove_container_success(docker_manager, mock_docker_client, tmp_path):
    """Test successful container removal."""
    name = "test-container"
    mock_container = MagicMock()
    mock_docker_client.containers.get.return_value = mock_container
    
    # Create a test data directory for the container
    container_data_dir = tmp_path / "data" / "containers" / name
    container_data_dir.mkdir(parents=True)
    test_file = container_data_dir / "test.txt"
    test_file.write_text("test content")
    
    docker_manager.remove_container(name)
    
    # Verify container was removed
    mock_docker_client.containers.get.assert_called_once_with(name)
    mock_container.remove.assert_called_once_with(force=True)
    
    # Verify data directory was cleaned up
    assert not container_data_dir.exists()

def test_remove_container_not_found(docker_manager, mock_docker_client):
    """Test removing non-existent container."""
    mock_docker_client.containers.get.side_effect = Exception("Container not found")
    
    with pytest.raises(Exception):
        docker_manager.remove_container("non-existent-container")

def test_create_container_with_version(docker_manager, mock_docker_client):
    """Test container creation with specific version."""
    name = "test-container"
    version = "11.315"
    
    # Mock container creation
    mock_container = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container
    
    container = docker_manager.create_container(name, version=version)
    
    # Verify container was created with correct version
    mock_docker_client.containers.create.assert_called_once()
    call_args = mock_docker_client.containers.create.call_args[1]
    assert call_args['image'] == f"{DockerManager.FOUNDRY_IMAGE}:{version}"

def test_create_container_default_version(docker_manager, mock_docker_client):
    """Test container creation with default version."""
    name = "test-container"
    
    # Mock container creation
    mock_container = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container
    
    container = docker_manager.create_container(name)
    
    # Verify container was created with latest version
    mock_docker_client.containers.create.assert_called_once()
    call_args = mock_docker_client.containers.create.call_args[1]
    assert call_args['image'] == f"{DockerManager.FOUNDRY_IMAGE}:latest"

def test_get_available_versions(docker_manager, mock_requests):
    """Test getting available Foundry VTT versions."""
    versions = docker_manager.get_available_versions()
    
    # Verify versions are returned and sorted
    assert len(versions) == 2  # Excluding 'latest'
    assert versions[0]['version'] == '11.316'
    assert versions[1]['version'] == '11.315'

def test_get_available_versions_error(docker_manager, mocker):
    """Test error handling when fetching versions fails."""
    mocker.patch('requests.get', side_effect=Exception("Network error"))
    
    versions = docker_manager.get_available_versions()
    assert versions == []

def test_migrate_container_success(docker_manager, mock_docker_client):
    """Test successful container migration to new version."""
    name = "test-container"
    new_version = "11.316"
    
    # Mock existing container
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.image.tags = [f"{DockerManager.FOUNDRY_IMAGE}:11.315"]
    mock_docker_client.containers.get.return_value = mock_container
    
    # Mock new container creation
    mock_new_container = MagicMock()
    mock_docker_client.containers.create.return_value = mock_new_container
    
    docker_manager.migrate_container(name, new_version)
    
    # Verify old container was stopped and removed
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()
    
    # Verify new container was created with correct version
    mock_docker_client.containers.create.assert_called_once()
    call_args = mock_docker_client.containers.create.call_args[1]
    assert call_args['image'] == f"{DockerManager.FOUNDRY_IMAGE}:{new_version}"

def test_migrate_container_not_found(docker_manager, mock_docker_client):
    """Test migration of non-existent container."""
    mock_docker_client.containers.get.side_effect = Exception("Container not found")
    
    with pytest.raises(Exception):
        docker_manager.migrate_container("non-existent-container", "11.316")

def test_list_containers_with_versions(docker_manager, mock_docker_client):
    """Test listing containers with version information."""
    # Create mock containers with versions
    mock_container1 = MagicMock()
    mock_container1.name = "container1"
    mock_container1.status = "running"
    mock_container1.image.tags = [f"{DockerManager.FOUNDRY_IMAGE}:11.315"]
    
    mock_container2 = MagicMock()
    mock_container2.name = "container2"
    mock_container2.status = "stopped"
    mock_container2.image.tags = [f"{DockerManager.FOUNDRY_IMAGE}:11.316"]
    
    mock_docker_client.containers.list.return_value = [mock_container1, mock_container2]
    
    # Call list_containers
    docker_manager.list_containers()
    
    # Verify containers were listed with versions
    mock_docker_client.containers.list.assert_called_once_with(all=True) 