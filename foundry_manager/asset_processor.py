#!/usr/bin/env python3
"""Asset processing module for Foundry VTT Instance Manager.

This module provides functionality for processing and optimizing assets before they are
stored in the shared assets directory. It includes support for image optimization and
conversion to WebP format.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

logger = logging.getLogger("foundry-manager")


class ImageProcessor(ABC):
    """Base class for image processors."""

    @abstractmethod
    def process(self, file_path: Path) -> Optional[Path]:
        """Process an image file.

        Args:
            file_path: Path to the image file to process.

        Returns:
            Path to the processed image file, or None if processing failed.
        """
        pass


class JPEGProcessor(ImageProcessor):
    """Processor for JPEG images."""

    def process(self, file_path: Path) -> Optional[Path]:
        """Convert JPEG to WebP with optimization.

        Args:
            file_path: Path to the JPEG file to process.

        Returns:
            Path to the processed WebP file, or None if processing failed.
        """
        try:
            with Image.open(file_path) as img:
                # Optimize JPEG
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background

                # Convert to WebP
                webp_path = file_path.with_suffix(".webp")
                img.save(webp_path, "WEBP", quality=85, method=6)
                return webp_path
        except Exception as e:
            logger.error(f"Error processing JPEG: {e}")
            return None


class PNGProcessor(ImageProcessor):
    """Processor for PNG images."""

    def process(self, file_path: Path) -> Optional[Path]:
        """Convert PNG to WebP with optimization.

        Args:
            file_path: Path to the PNG file to process.

        Returns:
            Path to the processed WebP file, or None if processing failed.
        """
        try:
            with Image.open(file_path) as img:
                # Convert to WebP
                webp_path = file_path.with_suffix(".webp")
                img.save(webp_path, "WEBP", quality=85, method=6)
                return webp_path
        except Exception as e:
            logger.error(f"Error processing PNG: {e}")
            return None


class GIFProcessor(ImageProcessor):
    """Processor for GIF images."""

    def process(self, file_path: Path) -> Optional[Path]:
        """Convert GIF to WebP with optimization.

        Args:
            file_path: Path to the GIF file to process.

        Returns:
            Path to the processed WebP file, or None if processing failed.
        """
        try:
            with Image.open(file_path) as img:
                # Convert to WebP
                webp_path = file_path.with_suffix(".webp")
                img.save(webp_path, "WEBP", quality=85, method=6)
                return webp_path
        except Exception as e:
            logger.error(f"Error processing GIF: {e}")
            return None


class AssetProcessor:
    """Handles asset optimization and conversion."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the AssetProcessor.

        Args:
            config: Configuration dictionary for the processor.
        """
        self.config = config
        self.image_processors = {
            "jpg": JPEGProcessor(),
            "jpeg": JPEGProcessor(),
            "png": PNGProcessor(),
            "gif": GIFProcessor(),
        }
        self.disable_processing = False

    def process_asset(self, file_path: Path, asset_type: str) -> Optional[Path]:
        """Process an asset based on its type.

        Args:
            file_path: Path to the asset file to process.
            asset_type: Type of the asset (e.g., 'images', 'audio', etc.).

        Returns:
            Path to the processed asset file, or the original file if no processing
            was performed or if processing was disabled.
        """
        if self.disable_processing:
            return file_path

        if asset_type == "images":
            return self._process_image(file_path)
        return file_path

    def _process_image(self, file_path: Path) -> Optional[Path]:
        """Process an image file.

        Args:
            file_path: Path to the image file to process.

        Returns:
            Path to the processed image file, or the original file if no processing
            was performed.
        """
        ext = file_path.suffix.lower().lstrip(".")
        processor = self.image_processors.get(ext)
        if processor:
            processed_path = processor.process(file_path)
            if processed_path:
                return processed_path
        return file_path
