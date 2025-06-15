# Docker Container Manager

A CLI tool for managing multiple Docker containers that share the same image but have individual data directories and a shared data directory.

## Features

- Create and manage multiple Docker containers from the same image
- Each container has its own isolated data directory
- Shared data directory accessible by all containers
- Easy-to-use CLI interface
- Container status monitoring

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```bash
# Create a new container
python docker_manager.py create --name my-container --image my-image

# List all containers
python docker_manager.py list

# Start a container
python docker_manager.py start --name my-container

# Stop a container
python docker_manager.py stop --name my-container

# Remove a container
python docker_manager.py remove --name my-container
```

## Configuration

The tool uses the following directory structure:
- `./data/shared/` - Shared data directory accessible by all containers
- `./data/containers/<container-name>/` - Individual container data directories

## Requirements

- Python 3.8+
- Docker installed and running
- Docker Python SDK
- Click
- Rich 

## Development with Cursor

Cursor is an AI-powered IDE that can help with development tasks. Here are some useful prompts you can use:

### Code Quality

- "Run flake8. For each issue found, understand the issue and surrounding code, explain the issue and your proposed solution, and finally implement your solution. Then rerun flake8 to verify the issue has been fixed. Repeat until all issues are fixed."
- "Run mypy. For each type error found, understand the issue and surrounding code, explain the issue and your proposed solution, and finally implement your solution. Then rerun mypy to verify the issue has been fixed. Repeat until all issues are fixed."
- "Run pytest. For each failing test, understand the failure and surrounding code, explain the issue and your proposed solution, and finally implement your solution. Then rerun pytest to verify the test passes. Repeat until all tests pass."

### Code Generation

- "Generate unit tests for the following function/class: [function/class name]"
- "Add docstrings to all public methods in [file name]"
- "Add type hints to all functions in [file name]"

### Code Review

- "Review the changes in [file name] and suggest improvements for code quality, performance, and maintainability"
- "Check for potential security issues in [file name]"
- "Suggest ways to improve error handling in [file name]"

### Documentation

- "Update the README.md with documentation for [feature/functionality]"
- "Generate API documentation for [module/class]"
- "Add inline comments to explain complex logic in [file name]"

### Refactoring

- "Refactor [function/class] to improve readability and maintainability"
- "Extract common functionality into a shared utility module"
- "Split [large function/class] into smaller, more focused components"

Remember to be specific in your prompts and provide context when needed. Cursor works best when given clear instructions and relevant information about the task at hand. 