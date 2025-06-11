from setuptools import setup, find_packages

setup(
    name="foundry-instance-manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "docker",
        "click",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "fim=foundry_manager.cli:cli",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A CLI tool for managing Docker containers",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/foundry-instance-manager",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
) 