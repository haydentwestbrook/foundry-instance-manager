"""Foundry VTT version management.

This module provides functionality for managing Foundry VTT versions, including:
- Getting available versions
- Getting the latest version
- Version validation
"""

import logging
from typing import List

logger = logging.getLogger("foundry-manager")

# List of available Foundry VTT versions
# This should be updated when new versions are released
AVAILABLE_VERSIONS = [
    "11.315",
    "11.316",
    "11.317",
    "11.318",
    "11.319",
    "11.320",
]


def get_versions() -> List[str]:
    """Get all available Foundry VTT versions.

    Returns:
        List of version strings.
    """
    return AVAILABLE_VERSIONS


def get_latest_version() -> str:
    """Get the latest available Foundry VTT version.

    Returns:
        Latest version string.
    """
    return AVAILABLE_VERSIONS[-1]


def is_valid_version(version: str) -> bool:
    """Check if a version string is valid.

    Args:
        version: Version string to check.

    Returns:
        True if the version is valid, False otherwise.
    """
    return version in AVAILABLE_VERSIONS
