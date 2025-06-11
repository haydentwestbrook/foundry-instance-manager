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