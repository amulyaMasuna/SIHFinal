"""
OpenCV Image Preprocessor for Legal Metrology AI Microservice
=============================================================
Provides high-performance image enhancement tailored for FMCG packaging labels:
- EXIF auto-rotation
- Dynamic aspect-ratio scaling for optimal OCR recognition
- CLAHE (Contrast Limited Adaptive Histogram Equalization) for packaging glare & plastic reflections
- Bilateral filtering to preserve crisp character edges while reducing sensor noise
- Deskewing and horizontal alignment via minAreaRect contour analysis
- Adaptive thresholding & shadow suppression
"""

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

import base64
from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger("preprocessor")


class ImagePreprocessor:
    def __init__(self, target_max_dim: int = 1800, target_min_dim: int = 600):
        if cv2 is None or np is None:
            raise ImportError(
                "OpenCV and NumPy are required for ImagePreprocessor. "
                "Install them via: pip install opencv-python-headless numpy"
            )
        self.target_max_dim = target_max_dim
        self.target_min_dim = target_min_dim

    def decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Decodes raw byte buffer into OpenCV BGR numpy array."""
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image buffer. Invalid image format.")
        return img

    def resize_for_ocr(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Scales image to optimal dimensions:
        - Downscales if max dimension exceeds target_max_dim (preserves memory & speed)
        - Upscales if label is too small (< target_min_dim) so small mandatory print remains legible
        """
        h, w = img.shape[:2]
        scale = 1.0

        if max(h, w) > self.target_max_dim:
            scale = self.target_max_dim / float(max(h, w))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            return img_resized, scale
        elif min(h, w) < self.target_min_dim:
            scale = self.target_min_dim / float(min(h, w))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            return img_resized, scale

        return img, scale

    def correct_skew(self, gray: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detects packaging label skew angle using Otsu thresholding + minAreaRect,
        and rotates to horizontal if skew exceeds threshold.
        """
        try:
            # Invert threshold to highlight text blocks as white contours
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find non-zero points (text pixels)
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 50:
                return gray, 0.0

            # Compute minimum area rectangle enclosing all text coordinates
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]

            # Normalize angle to range [-45, 45]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Only rotate if skew is notable (> 1.0 degree and < 45 degrees)
            if abs(angle) > 1.0 and abs(angle) < 45.0:
                h, w = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
                return rotated, angle
        except Exception as e:
            logger.warning(f"Deskewing skipped due to error: {e}")

        return gray, 0.0

    def apply_clahe(self, gray: np.ndarray, clip_limit: float = 2.5, tile_size: int = 8) -> np.ndarray:
        """
        Applies Contrast Limited Adaptive Histogram Equalization (CLAHE).
        Crucial for FMCG pouches with packaging glare, foil reflections, and shadows.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        return clahe.apply(gray)

    def remove_glare_and_shadows(self, gray: np.ndarray) -> np.ndarray:
        """
        Removes uneven background illumination using morphological opening,
        normalizing bright packaging spots and heavy shadows.
        """
        dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
        bg_img = cv2.medianBlur(dilated, 21)
        diff_img = 255 - cv2.absdiff(gray, bg_img)
        norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return norm_img

    def denoise_preserve_edges(self, gray: np.ndarray) -> np.ndarray:
        """
        Bilateral filter removes high-frequency packaging texture/noise
        while preserving sharp text edge boundaries.
        """
        return cv2.bilateralFilter(gray, d=7, sigmaColor=75, sigmaSpace=75)

    def adaptive_binarize(self, gray: np.ndarray) -> np.ndarray:
        """Generates crisp binary image via adaptive Gaussian thresholding."""
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )

    def preprocess(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Executes full preprocessing pipeline.
        Returns:
            - 'ocr_ready_image': BGR 3-channel image ready for PaddleOCR input.
            - 'gray_enhanced': Contrast-enhanced grayscale image.
            - 'scale_factor': Scaling ratio applied.
            - 'skew_angle': Corrected skew angle in degrees.
            - 'original_dims': (width, height) of uploaded image.
            - 'processed_dims': (width, height) after preprocessing.
        """
        # 1. Decode
        orig_bgr = self.decode_image(image_bytes)
        h_orig, w_orig = orig_bgr.shape[:2]

        # 2. Rescaling
        resized_bgr, scale = self.resize_for_ocr(orig_bgr)
        h_proc, w_proc = resized_bgr.shape[:2]

        # 3. Grayscale
        gray = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2GRAY)

        # 4. Deskew
        gray_deskewed, skew_angle = self.correct_skew(gray)

        # 5. Denoise with edge preservation
        denoised = self.denoise_preserve_edges(gray_deskewed)

        # 6. Glare & shadow illumination normalization
        glare_removed = self.remove_glare_and_shadows(denoised)

        # 7. CLAHE contrast enhancement
        enhanced_gray = self.apply_clahe(glare_removed, clip_limit=2.5, tile_size=8)

        # 8. Adaptive binarization (for high-contrast fallback)
        binary = self.adaptive_binarize(enhanced_gray)

        # 9. Convert enhanced gray back to 3-channel BGR for PaddleOCR
        ocr_ready_bgr = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)

        return {
            "ocr_ready_image": ocr_ready_bgr,
            "gray_enhanced": enhanced_gray,
            "binary_image": binary,
            "scale_factor": scale,
            "skew_angle": round(skew_angle, 2),
            "original_dims": {"width": w_orig, "height": h_orig},
            "processed_dims": {"width": w_proc, "height": h_proc}
        }

    def image_to_base64(self, img: np.ndarray, format_ext: str = ".jpg") -> str:
        """Converts an OpenCV image array to base64 data URI string."""
        success, encoded_img = cv2.imencode(format_ext, img)
        if not success:
            return ""
        b64 = base64.b64encode(encoded_img).decode("utf-8")
        mime = "image/jpeg" if format_ext.lower() in [".jpg", ".jpeg"] else "image/png"
        return f"data:{mime};base64,{b64}"
