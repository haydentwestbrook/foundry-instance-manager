"""Tests for the instance record management functionality."""

import json
from pathlib import Path

import pytest

from foundry_manager.instance_record_manager import (
    InstanceRecord,
    InstanceRecordManager,
)


@pytest.fixture
def base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return tmp_path


@pytest.fixture
def record_manager(base_dir):
    """Create an instance record manager."""
    return InstanceRecordManager(base_dir=base_dir)


@pytest.fixture
def test_record():
    """Create a test instance record."""
    return InstanceRecord(
        name="test-instance",
        version="11.0.0",
        data_dir=Path("/test/data"),
        port=30000,
        status="running",
    )


class TestInstanceRecordManager:
    """Test suite for InstanceRecordManager class."""

    def test_add_record(self, record_manager, test_record):
        """Test adding an instance record."""
        # Add record
        record_manager.add_record(test_record)

        # Verify record was added
        record = record_manager.get_record("test-instance")
        assert record.name == test_record.name
        assert record.version == test_record.version
        assert record.data_dir == test_record.data_dir
        assert record.port == test_record.port
        assert record.status == test_record.status

    def test_get_record(self, record_manager, test_record):
        """Test getting a record."""
        # Add record
        record_manager.add_record(test_record)

        # Get record
        record = record_manager.get_record("test-instance")
        assert record == test_record

    def test_get_nonexistent_record(self, record_manager):
        """Test getting a non-existent record."""
        record = record_manager.get_record("nonexistent-instance")
        assert record is None

    def test_get_all_records(self, record_manager):
        """Test getting all records."""
        # Create test records
        records = [
            InstanceRecord(
                name="test-instance-1",
                version="11.0.0",
                data_dir=Path("/test/data1"),
                port=30000,
                status="running",
            ),
            InstanceRecord(
                name="test-instance-2",
                version="11.1.0",
                data_dir=Path("/test/data2"),
                port=30001,
                status="stopped",
            ),
        ]

        # Add records
        for record in records:
            record_manager.add_record(record)

        # Get all records
        all_records = record_manager.get_all_records()

        # Verify records
        assert len(all_records) == 2
        assert all_records[0].name == "test-instance-1"
        assert all_records[1].name == "test-instance-2"

    def test_update_status(self, record_manager, test_record):
        """Test updating record status."""
        # Add record
        record_manager.add_record(test_record)

        # Update status
        record_manager.update_status("test-instance", "stopped")

        # Verify status was updated
        record = record_manager.get_record("test-instance")
        assert record.status == "stopped"

    def test_update_version(self, record_manager, test_record):
        """Test updating record version."""
        # Add record
        record_manager.add_record(test_record)

        # Update version
        record_manager.update_version("test-instance", "11.1.0")

        # Verify version was updated
        record = record_manager.get_record("test-instance")
        assert record.version == "11.1.0"

    def test_remove_record(self, record_manager, test_record):
        """Test removing an instance record."""
        # Add record
        record_manager.add_record(test_record)

        # Remove record
        record_manager.remove_record("test-instance")

        # Verify record was removed
        record = record_manager.get_record("test-instance")
        assert record is None


class TestRecordPersistence:
    """Test suite for record persistence functionality.

    This class contains tests for the persistence of instance records between manager
    instances. It tests both successful record persistence scenarios and error cases.

    The tests cover:
    - Persistence of records between manager instances
    - Format of the record file
    """

    def test_record_persistence(self, record_manager, test_record):
        """Test that records persist between manager instances."""
        # Add record
        record_manager.add_record(test_record)

        # Create new manager instance
        new_manager = InstanceRecordManager(base_dir=record_manager.base_dir)

        # Verify record exists in new manager
        record = new_manager.get_record("test-instance")
        assert record == test_record

    def test_record_file_format(self, record_manager, test_record):
        """Test the format of the record file."""
        # Add record
        record_manager.add_record(test_record)

        # Read record file
        record_file = record_manager.base_dir / "instances.json"
        with open(record_file) as f:
            data = json.load(f)

        # Verify file format
        assert "test-instance" in data
        record_data = data["test-instance"]
        assert record_data["version"] == test_record.version
        assert record_data["data_dir"] == str(test_record.data_dir)
        assert record_data["port"] == test_record.port
        assert record_data["status"] == test_record.status


class TestErrorHandling:
    """Test suite for error handling functionality.

    This class contains tests for the error handling functionality of the
    InstanceRecordManager. It tests both successful error handling scenarios and
    error cases.

    The tests cover:
    - Updating a non-existent record
    - Removing a non-existent record
    """

    def test_update_nonexistent_record(self, record_manager):
        """Test updating a non-existent record."""
        # Attempt to update status
        record_manager.update_status("nonexistent-instance", "running")
        # Should not raise an error, just do nothing

        # Attempt to update version
        record_manager.update_version("nonexistent-instance", "11.1.0")
        # Should not raise an error, just do nothing

    def test_remove_nonexistent_record(self, record_manager):
        """Test removing a non-existent record."""
        # Attempt to remove record
        record_manager.remove_record("nonexistent-instance")
        # Should not raise an error, just do nothing

    def test_corrupted_record_file(self, record_manager, test_record):
        """Test handling of corrupted record file."""
        # Add record
        record_manager.add_record(test_record)

        # Corrupt the record file
        record_file = record_manager.base_dir / "instances.json"
        with open(record_file, "w") as f:
            f.write("invalid json")

        # Create new manager instance
        new_manager = InstanceRecordManager(base_dir=record_manager.base_dir)

        # Verify manager handles corruption gracefully
        records = new_manager.get_all_records()
        assert len(records) == 0  # Should start with empty records after corruption
