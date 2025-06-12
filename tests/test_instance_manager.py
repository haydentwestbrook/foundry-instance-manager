import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from foundry_manager.foundry_instance_manager import FoundryInstanceManager, FoundryInstance
from foundry_manager.docker_manager import ContainerNotFoundError
from foundry_manager.instance_record import InstanceRecord

@pytest.fixture
def base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return tmp_path

@pytest.fixture
def mock_docker_manager():
    """Create a mock docker manager."""
    with patch('foundry_manager.foundry_instance_manager.DockerManager') as mock:
        manager = mock.return_value
        yield manager

@pytest.fixture
def mock_record_manager():
    """Create a mock record manager."""
    with patch('foundry_manager.foundry_instance_manager.InstanceRecordManager') as mock:
        manager = mock.return_value
        yield manager

@pytest.fixture
def instance_manager(base_dir, mock_docker_manager, mock_record_manager):
    """Create an instance manager with mocked dependencies."""
    return FoundryInstanceManager(base_dir=base_dir)

class TestInstanceCreation:
    def test_create_instance_success(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test successful instance creation."""
        # Mock container
        mock_container = MagicMock()
        mock_container.status = "created"
        mock_docker_manager.create_container.return_value = mock_container

        # Create instance
        instance = instance_manager.create_instance(
            name="test-instance",
            version="11.0.0",
            port=30000,
            environment={"TEST_VAR": "test_value"}
        )

        # Verify instance
        assert instance.name == "test-instance"
        assert instance.version == "11.0.0"
        assert instance.port == 30000
        assert instance.container == mock_container

        # Verify docker manager calls
        mock_docker_manager.create_container.assert_called_once()
        mock_record_manager.add_record.assert_called_once()

    def test_create_instance_existing_container(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test creating instance when container already exists."""
        # Mock existing container
        mock_container = MagicMock()
        mock_docker_manager.get_container.return_value = mock_container

        # Create instance
        instance = instance_manager.create_instance(
            name="test-instance",
            version="11.0.0"
        )

        # Verify old container was removed
        mock_docker_manager.remove_container.assert_called_once_with("test-instance")
        mock_docker_manager.create_container.assert_called_once()

    def test_create_instance_cleanup_on_error(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test cleanup when instance creation fails."""
        # Mock container creation failure
        mock_docker_manager.create_container.side_effect = Exception("Test error")

        # Attempt to create instance
        with pytest.raises(Exception):
            instance_manager.create_instance("test-instance")

        # Verify cleanup
        mock_docker_manager.remove_container.assert_called_once_with("test-instance")

class TestInstanceManagement:
    def test_get_instance(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test getting an instance."""
        # Mock record and container
        mock_record = InstanceRecord(
            name="test-instance",
            version="11.0.0",
            data_dir=Path("/test/data"),
            port=30000,
            status="running"
        )
        mock_container = MagicMock()
        mock_record_manager.get_record.return_value = mock_record
        mock_docker_manager.get_container.return_value = mock_container

        # Get instance
        instance = instance_manager.get_instance("test-instance")

        # Verify instance
        assert instance.name == "test-instance"
        assert instance.version == "11.0.0"
        assert instance.container == mock_container

    def test_list_instances(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test listing all instances."""
        # Mock records and containers
        mock_records = [
            InstanceRecord(
                name="test-instance-1",
                version="11.0.0",
                data_dir=Path("/test/data1"),
                port=30000,
                status="running"
            ),
            InstanceRecord(
                name="test-instance-2",
                version="11.1.0",
                data_dir=Path("/test/data2"),
                port=30001,
                status="stopped"
            )
        ]
        mock_container = MagicMock()
        mock_record_manager.get_all_records.return_value = mock_records
        mock_docker_manager.get_container.return_value = mock_container

        # List instances
        instances = instance_manager.list_instances()

        # Verify instances
        assert len(instances) == 2
        assert instances[0].name == "test-instance-1"
        assert instances[1].name == "test-instance-2"

class TestInstanceOperations:
    def test_start_instance(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test starting an instance."""
        # Mock instance
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        instance_manager.get_instance = MagicMock(return_value=mock_instance)

        # Start instance
        instance_manager.start_instance("test-instance")

        # Verify operations
        mock_docker_manager.start_container.assert_called_once_with("test-instance")
        mock_record_manager.update_status.assert_called_once_with("test-instance", "running")

    def test_stop_instance(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test stopping an instance."""
        # Mock instance
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        instance_manager.get_instance = MagicMock(return_value=mock_instance)

        # Stop instance
        instance_manager.stop_instance("test-instance")

        # Verify operations
        mock_docker_manager.stop_container.assert_called_once_with("test-instance")
        mock_record_manager.update_status.assert_called_once_with("test-instance", "stopped")

    def test_remove_instance(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test removing an instance."""
        # Mock instance
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.status = "stopped"
        mock_instance.data_dir = Path("/test/data")
        instance_manager.get_instance = MagicMock(return_value=mock_instance)

        # Remove instance
        instance_manager.remove_instance("test-instance")

        # Verify operations
        mock_docker_manager.remove_container.assert_called_once_with("test-instance")
        mock_record_manager.remove_record.assert_called_once_with("test-instance")

    def test_migrate_instance(self, instance_manager, mock_docker_manager, mock_record_manager):
        """Test migrating an instance to a new version."""
        # Mock instance
        mock_instance = MagicMock(spec=FoundryInstance)
        mock_instance.name = "test-instance"
        mock_instance.status = "running"
        mock_instance.data_dir = Path("/test/data")
        mock_instance.port = 30000
        instance_manager.get_instance = MagicMock(return_value=mock_instance)

        # Mock new container
        mock_container = MagicMock()
        mock_docker_manager.create_container.return_value = mock_container

        # Migrate instance
        instance_manager.migrate_instance("test-instance", "11.1.0")

        # Verify operations
        mock_docker_manager.stop_container.assert_called_once_with("test-instance")
        mock_docker_manager.remove_container.assert_called_once_with("test-instance")
        mock_docker_manager.create_container.assert_called_once()
        mock_record_manager.update_version.assert_called_once_with("test-instance", "11.1.0")
        mock_docker_manager.start_container.assert_called_once_with("test-instance")

class TestErrorHandling:
    def test_get_nonexistent_instance(self, instance_manager, mock_record_manager):
        """Test getting a non-existent instance."""
        mock_record_manager.get_record.return_value = None
        instance = instance_manager.get_instance("nonexistent-instance")
        assert instance is None

    def test_start_nonexistent_instance(self, instance_manager, mock_record_manager):
        """Test starting a non-existent instance."""
        mock_record_manager.get_record.return_value = None
        with pytest.raises(ValueError, match="Instance nonexistent-instance not found"):
            instance_manager.start_instance("nonexistent-instance")

    def test_stop_nonexistent_instance(self, instance_manager, mock_record_manager):
        """Test stopping a non-existent instance."""
        mock_record_manager.get_record.return_value = None
        with pytest.raises(ValueError, match="Instance nonexistent-instance not found"):
            instance_manager.stop_instance("nonexistent-instance")

    def test_remove_nonexistent_instance(self, instance_manager, mock_record_manager):
        """Test removing a non-existent instance."""
        mock_record_manager.get_record.return_value = None
        with pytest.raises(ValueError, match="Instance nonexistent-instance not found"):
            instance_manager.remove_instance("nonexistent-instance")

    def test_migrate_nonexistent_instance(self, instance_manager, mock_record_manager):
        """Test migrating a non-existent instance."""
        mock_record_manager.get_record.return_value = None
        with pytest.raises(ValueError, match="Instance nonexistent-instance not found"):
            instance_manager.migrate_instance("nonexistent-instance", "11.1.0") 