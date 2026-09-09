"""
Unit Tests for OpenCV Drawing Preprocessing & Deskew
"""

import pytest
import numpy as np
import cv2
from vision.preprocessing import ImagePreprocessor

def test_grayscale_conversion():
    # 3-channel color image
    color_img = np.zeros((100, 100, 3), dtype=np.uint8)
    color_img[:, :] = [255, 200, 150]
    gray = ImagePreprocessor.to_grayscale(color_img)
    assert len(gray.shape) == 2
    assert gray.shape == (100, 100)

def test_adaptive_threshold_and_noise_removal():
    # White background with black text/lines
    img = np.ones((200, 200), dtype=np.uint8) * 255
    # Draw black horizontal line
    img[98:102, 20:180] = 0
    # Add small pepper noise dot
    img[40, 40] = 0

    binary = ImagePreprocessor.adaptive_threshold(img)
    assert binary[100, 100] == 255  # Line should be inverted to white on black

    clean = ImagePreprocessor.remove_noise(binary, kernel_size=2)
    assert clean[40, 40] == 0       # Isolated noise pixel removed
    assert clean[100, 100] == 255   # Line preserved

def test_deskew_rotated_image():
    # Create image with horizontal line, then rotate by 5 degrees
    img = np.zeros((300, 300), dtype=np.uint8)
    img[148:152, 50:250] = 255

    # Rotate by 5 degrees
    rot_matrix = cv2.getRotationMatrix2D((150, 150), 5.0, 1.0)
    rotated = cv2.warpAffine(img, rot_matrix, (300, 300))

    angle = ImagePreprocessor.estimate_skew_angle(rotated)
    # Estimated angle should be close to 5° (or -5° depending on coordinate orientation)
    assert abs(abs(angle) - 5.0) < 1.0
