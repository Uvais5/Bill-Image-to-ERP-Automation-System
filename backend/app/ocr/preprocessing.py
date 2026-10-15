import cv2
import numpy as np


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Decodes raw image bytes into an OpenCV BGR image in-memory."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image. File might be corrupted or in an unsupported format.")
    return img


def resize_image_if_needed(img: np.ndarray, max_dim: int = 2000, min_dim: int = 800) -> np.ndarray:
    """
    Resizes image maintaining aspect ratio:
    - Downscales if larger than max_dim to maintain fast CPU inference.
    - Upscales small invoices (< min_dim) to improve OCR recognition on low-res receipts.
    """
    h, w = img.shape[:2]
    max_current = max(h, w)
    min_current = min(h, w)
    
    if max_current > max_dim:
        scale = max_dim / float(max_current)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    elif min_current < min_dim and max_current * 1.5 <= max_dim:
        scale = min_dim / float(min_current)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    return img


def deskew_image(img: np.ndarray) -> np.ndarray:
    """Corrects slight skew angles in document images."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Invert colors: text becomes foreground
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        
        # Find coordinates of all non-zero pixels
        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            return img
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # Determine angle correction
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle
            
        # Only adjust if angle is moderate (avoids rotating 90 degrees if text is vertical)
        if abs(angle) > 0.5 and abs(angle) < 20.0:
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
    except Exception:
        pass
    return img


def enhance_contrast(img: np.ndarray) -> np.ndarray:
    """Enhances text contrast using CLAHE in LAB color space."""
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return enhanced
    except Exception:
        return img


def preprocess_pipeline(image_bytes: bytes) -> np.ndarray:
    """
    Executes the stateless image preprocessing pipeline:
    Input bytes -> Decode -> Resize -> Deskew -> Contrast Enhancement
    """
    img = decode_image(image_bytes)
    img = resize_image_if_needed(img)
    img = deskew_image(img)
    img = enhance_contrast(img)
    return img
