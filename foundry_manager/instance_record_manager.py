"""Instance Record Management Module.

This module provides functionality for managing records of Foundry VTT instances.
It handles the persistence and retrieval of instance metadata including:
- Instance names and versions
- Data directory locations
- Port configurations
- Instance status

The module uses a JSON file to store instance records and provides methods for:
- Adding new instance records
- Retrieving specific instance records
- Listing all instance records
- Updating existing records
- Removing instance records

The records are stored in a file called 'instances.json' in the base directory
specified during initialization.

Example usage:
    record_manager = InstanceRecordManager(Path('/path/to/base/dir'))
    record = InstanceRecord(
        name='my-instance',
        version='11.0.0',
        data_dir=Path('/path/to/data'),
        port=30000
    )
    record_manager.add_record(record)
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("foundry-manager")


@dataclass
class InstanceRecord:
    """Record of a Foundry instance."""

    name: str
    version: str
    data_dir: Path
    port: int
    status: str = "stopped"


class InstanceRecordManager:
    """Manages records of Foundry instances."""

    def __init__(self, base_dir: Path):
        """Initialize the InstanceRecordManager with a base directory."""
        self.base_dir = base_dir
        self.records_file = base_dir / "instances.json"
        self._records: Dict[str, InstanceRecord] = {}
        self._load_records()

    def _load_records(self) -> None:
        """Load instance records from file."""
        try:
            if self.records_file.exists():
                with open(self.records_file) as f:
                    data = json.load(f)
                    self._records = {
                        name: InstanceRecord(
                            name=record["name"],
                            version=record["version"],
                            data_dir=Path(record["data_dir"]),
                            port=record["port"],
                            status=record.get("status", "stopped"),
                        )
                        for name, record in data.items()
                    }
        except Exception as e:
            logger.error(f"Failed to load instance records: {e}")
            self._records = {}

    def _save_records(self) -> None:
        """Save instance records to file."""
        try:
            self.records_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.records_file, "w") as f:
                json.dump(
                    {name: asdict(record) for name, record in self._records.items()},
                    f,
                    indent=4,
                    default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save instance records: {e}")

    def add_record(self, record: InstanceRecord) -> None:
        """Add or update an instance record."""
        self._records[record.name] = record
        self._save_records()

    def remove_record(self, name: str) -> None:
        """Remove an instance record."""
        if name in self._records:
            del self._records[name]
            self._save_records()

    def get_record(self, name: str) -> Optional[InstanceRecord]:
        """Get an instance record by name."""
        return self._records.get(name)

    def get_all_records(self) -> List[InstanceRecord]:
        """Get all instance records."""
        return list(self._records.values())

    def update_status(self, name: str, status: str) -> None:
        """Update the status of an instance."""
        if name in self._records:
            self._records[name].status = status
            self._save_records()

    def update_version(self, name: str, version: str) -> None:
        """Update the version of an instance."""
        if name in self._records:
            self._records[name].version = version
            self._save_records()
