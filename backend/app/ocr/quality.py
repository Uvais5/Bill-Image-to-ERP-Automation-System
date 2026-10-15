from dataclasses import dataclass
from typing import Optional
import cv2
import numpy as np
from ..config import settings


@dataclass
class QualityReport:
    is_clear: bool
    blur_score: float
    mean_brightness: float
    width: int
    height: int
    recommend_vlm_direct: bool
    warning_message: Optional[str] = None


class ImageQualityChecker:
    def __init__(self, blur_threshold: float = settings.BLUR_THRESHOLD):
        self.blur_threshold = blur_threshold

    def analyze(self, img: np.ndarray) -> QualityReport:
        """
        Analyzes image quality using OpenCV metrics:
        - Variance of Laplacian for blur detection
        - Grayscale mean intensity for lighting conditions
        - Resolution constraints
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 1. Blur calculation (Laplacian variance)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 2. Brightness & contrast evaluation
        mean_brightness = float(np.mean(gray))
        std_contrast = float(np.std(gray))

        is_dark = mean_brightness < 45.0
        is_overexposed = mean_brightness > 252.0 and std_contrast < 8.0
        is_blurry = blur_score < self.blur_threshold and not is_dark
        is_low_res = min(h, w) < 350

        recommend_vlm = is_blurry or is_dark or is_overexposed or is_low_res
        is_clear = not recommend_vlm

        warning = None
        if is_dark:
            warning = "Image is underexposed or in low lighting."
        elif is_overexposed:
            warning = "Image is overexposed with high glare."
        elif is_blurry:
            warning = f"Image appears blurry (sharpness score: {blur_score:.1f})."
        elif is_low_res:
            warning = f"Image resolution ({w}x{h}) is relatively low."

        return QualityReport(
            is_clear=is_clear,
            blur_score=round(blur_score, 2),
            mean_brightness=round(mean_brightness, 2),
            width=w,
            height=h,
            recommend_vlm_direct=recommend_vlm,
            warning_message=warning,
        )


quality_checker = ImageQualityChecker()
