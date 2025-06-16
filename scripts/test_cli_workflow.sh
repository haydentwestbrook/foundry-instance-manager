#!/bin/bash
set -e

# Test the CLI workflow
echo "Testing CLI workflow..."

# Test basic commands
foundry-manager --version
foundry-manager --help

# Test instance creation
foundry-manager create test-instance --version 11.300
foundry-manager list

# Test instance management
foundry-manager start test-instance
foundry-manager status test-instance
foundry-manager stop test-instance

# Test instance deletion
foundry-manager delete test-instance --force

echo "CLI workflow tests completed successfully!"
