import cv2
import numpy as np
import pytest
from backend.app.ocr.quality import ImageQualityChecker


def test_quality_checker_clear_image():
    checker = ImageQualityChecker()
    # High-contrast sharp image with clear text
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Sharp Invoice Text", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

    report = checker.analyze(img)
    assert report.is_clear is True
    assert report.blur_score > 50.0
    assert report.recommend_vlm_direct is False


def test_quality_checker_blurry_image():
    checker = ImageQualityChecker(blur_threshold=100.0)
    # Start with text, then apply heavy gaussian blur
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Blurry Text", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    blurry_img = cv2.GaussianBlur(img, (25, 25), 0)

    report = checker.analyze(blurry_img)
    assert report.recommend_vlm_direct is True
    assert report.warning_message is not None
    assert "blurry" in report.warning_message.lower()


def test_quality_checker_dark_image():
    checker = ImageQualityChecker()
    # Almost black image
    dark_img = np.ones((500, 500, 3), dtype=np.uint8) * 20

    report = checker.analyze(dark_img)
    assert report.recommend_vlm_direct is True
    assert report.warning_message is not None
    assert "underexposed" in report.warning_message.lower()
