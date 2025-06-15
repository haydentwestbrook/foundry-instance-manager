#!/bin/bash
set -e

# Use a temporary HOME to avoid affecting real user data
temp_home=$(mktemp -d)
export HOME="$temp_home"
echo "Using temporary HOME: $HOME"

# Set up variables
BASE_DIR="/tmp/foundry-data"
INSTANCE="test-instance"
PORT=30001
ADMIN_KEY="testkey"
SYSTEM_URL="https://example.com/system.zip"
SYSTEM_ID="dnd5e"
FOUNDRY_VERSION="13.345.0"

# Helper to print and run commands
echo_and_run() {
  echo -e "\n===== $* ====="
  "$@"
}

# 1. Show CLI help
echo_and_run python -m foundry_manager.cli --help

echo_and_run python -m foundry_manager.cli systems --help

# 2. Set base dir
echo_and_run python -m foundry_manager.cli set-base-dir --base-dir "$BASE_DIR"

# 3. Set credentials
echo_and_run python -m foundry_manager.cli set-credentials --username testuser --password testpass

# 4. Create an instance
echo_and_run python -m foundry_manager.cli create "$INSTANCE" --version "$FOUNDRY_VERSION" --port "$PORT" --admin-key "$ADMIN_KEY" --proxy-port 8443

# 5. List instances
echo_and_run python -m foundry_manager.cli list-instances

# 6. Start and stop instance
echo_and_run python -m foundry_manager.cli start "$INSTANCE"
echo_and_run python -m foundry_manager.cli stop "$INSTANCE"

# 7. Systems commands (install, list, remove)
echo_and_run python -m foundry_manager.cli systems install-system "$INSTANCE" "$SYSTEM_URL" || true
# List systems (should show installed system if SYSTEM_URL is valid)
echo_and_run python -m foundry_manager.cli systems list-systems "$INSTANCE" || true
# Remove system (will fail if not actually installed)
echo_and_run python -m foundry_manager.cli systems remove-system "$INSTANCE" "$SYSTEM_ID" || true

# Cleanup
echo "Cleaning up temporary HOME: $HOME"
rm -rf "$temp_home"
echo "Done." 