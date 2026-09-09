"""
QS Quantification Engine — Image Preprocessing Engine
Performs contrast normalization, adaptive thresholding, morphological line enhancement, and deskew.
Enforces Blueprint Section 12 (Module 6 — Raster Preprocessing).
"""

from __future__ import annotations
import cv2
import numpy as np

class ImagePreprocessor:
    """Preprocesses scanned/raster drawing sheets to isolate linework and text."""

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Converts image to grayscale if not already."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def adaptive_threshold(gray: np.ndarray, block_size: int = 15, c: int = 4) -> np.ndarray:
        """Applies adaptive Gaussian thresholding to separate black linework from paper texture."""
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            block_size,
            c
        )

    @staticmethod
    def remove_noise(binary: np.ndarray, kernel_size: int = 2) -> np.ndarray:
        """Removes small pepper noise while preserving continuous lines."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    @staticmethod
    def estimate_skew_angle(binary: np.ndarray) -> float:
        """Estimates skew angle in degrees using minimum area rectangle around non-zero pixels."""
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 50:
            return 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45.0:
            angle = -(90.0 + angle)
        else:
            angle = -angle

        # If angle is negligible (< 0.2 degrees), ignore
        return float(angle) if abs(angle) > 0.2 else 0.0

    @staticmethod
    def deskew(image: np.ndarray, angle_deg: float) -> np.ndarray:
        """Rotates image around center to compensate for scanner skew."""
        if abs(angle_deg) < 0.2:
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        return cv2.warpAffine(
            image,
            rot_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

    @classmethod
    def clean_drawing_image(cls, image: np.ndarray) -> tuple[np.ndarray, float]:
        """Full preprocessing pipeline: gray -> threshold -> deskew -> cleaned binary."""
        gray = cls.to_grayscale(image)
        binary = cls.adaptive_threshold(gray)
        clean = cls.remove_noise(binary)
        skew = cls.estimate_skew_angle(clean)
        if abs(skew) > 0.2:
            clean = cls.deskew(clean, skew)
        return clean, skew
