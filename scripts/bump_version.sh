#!/bin/bash
set -e

# Get the version type from command line argument
VERSION_TYPE=${1:-patch}

# Validate version type
if [[ ! "$VERSION_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Error: Version type must be one of: major, minor, patch"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(python -c "from foundry_manager import __version__; print(__version__)")

# Generate changelog
echo "Generating changelog..."
git-changelog -o CHANGELOG.md

# Bump version
bump2version --allow-dirty $VERSION_TYPE

# Get new version
NEW_VERSION=$(python -c "from foundry_manager import __version__; print(__version__)")

echo "Version bumped from $CURRENT_VERSION to $NEW_VERSION"

# Create git tag
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo "Created git tag v$NEW_VERSION"
