"""
Phase 3 Image Loading Module
Load and preprocess cheque images safely without modifying source files
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import tensorflow as tf


class ImageLoader:
    """Load and preprocess cheque images"""

    # Approved input size for Phase 3 training
    MOBILENETV2_INPUT_HEIGHT = 256
    MOBILENETV2_INPUT_WIDTH = 128
    MOBILENETV2_INPUT_CHANNELS = 3

    def __init__(self):
        self.loaded_images = {}  # Cache for testing only

    def load_image(self, image_path: str, verbose: bool = False) -> Optional[np.ndarray]:
        """
        Load a TIF image as numpy array (RGB).
        Does not modify the source file.

        Args:
            image_path: Path to TIF image
            verbose: Print loading details

        Returns:
            numpy array (RGB, uint8, [0, 255]) or None if loading fails
        """
        try:
            image_path = Path(image_path)

            if not image_path.exists():
                if verbose:
                    print(f"✗ Image not found: {image_path}")
                return None

            # Load image without modifying source
            with Image.open(image_path) as img:
                # Convert to RGB (guarantees 3 channels)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Convert to numpy array
                image_array = np.array(img, dtype=np.uint8)

            if verbose:
                print(f"✓ Loaded: {image_path.name} | Shape: {image_array.shape}")

            return image_array

        except Exception as e:
            if verbose:
                print(f"✗ Error loading {image_path}: {e}")
            return None

    def preprocess_for_mobilenetv2(self, image_array: np.ndarray) -> np.ndarray:
        """
        Preprocess image for MobileNetV2:
        1. Resize to 256 × 128
        2. Apply MobileNetV2 normalization

        Args:
            image_array: numpy array of shape (H, W, 3), uint8, values [0, 255]

        Returns:
            preprocessed array of shape (256, 128, 3), float32, values ≈ [-1, 1]
        """
        # Step 1: Resize to approved input size (256, 128)
        # Convert to tensor for TF operations
        image_tensor = tf.convert_to_tensor(image_array, dtype=tf.uint8)

        # Resize to (256, 128) - do NOT modify source file
        # tf.image.resize() produces float32 values in [0, 255]
        resized = tf.image.resize(
            image_tensor,
            size=[self.MOBILENETV2_INPUT_HEIGHT, self.MOBILENETV2_INPUT_WIDTH],
            method='bilinear'
        )

        # Step 2: Apply MobileNetV2 preprocessing
        # Pass float32 [0, 255] values directly to preprocess_input
        # MobileNetV2 preprocess_input converts to ≈ [-1, 1]
        preprocessed = tf.keras.applications.mobilenet_v2.preprocess_input(
            resized
        )

        return preprocessed.numpy()

    def get_mobilenetv2_input_shape(self) -> Tuple[int, int, int]:
        """
        Get expected input shape for MobileNetV2 (Phase 3 approved size).

        Returns:
            Tuple of (height, width, channels) = (256, 128, 3)
        """
        return (
            self.MOBILENETV2_INPUT_HEIGHT,
            self.MOBILENETV2_INPUT_WIDTH,
            self.MOBILENETV2_INPUT_CHANNELS
        )

    def validate_preprocessing_output(self, preprocessed: np.ndarray) -> bool:
        """
        Validate preprocessed image meets MobileNetV2 requirements.

        Args:
            preprocessed: preprocessed image array

        Returns:
            True if valid, False otherwise
        """
        # Check shape: must be (256, 128, 3)
        expected_shape = (
            self.MOBILENETV2_INPUT_HEIGHT,
            self.MOBILENETV2_INPUT_WIDTH,
            self.MOBILENETV2_INPUT_CHANNELS
        )

        if preprocessed.shape != expected_shape:
            return False

        # Check dtype: must be float32
        if preprocessed.dtype != np.float32:
            return False

        # Check value range: MobileNetV2 preprocessing outputs ≈ [-1, 1]
        # Allow slight margin for numerical precision
        min_val = np.min(preprocessed)
        max_val = np.max(preprocessed)

        if min_val < -2.0 or max_val > 2.0:
            return False

        return True
