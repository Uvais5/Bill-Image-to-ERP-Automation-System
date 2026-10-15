from typing import List, Tuple
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from ..schemas.invoice import OCRBox


class OCREngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            cls._instance._engine = RapidOCR()
        return cls._instance

    def run_ocr(self, img: np.ndarray) -> List[OCRBox]:
        """
        Runs RapidOCR on an in-memory image array.
        Returns a list of OCRBox models containing text, confidence, and bounding box.
        """
        results, _ = self._engine(img)
        ocr_boxes: List[OCRBox] = []

        if not results:
            return ocr_boxes

        for item in results:
            dt_boxes, text, score = item
            
            # dt_boxes is 4 polygon points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            pts = np.array(dt_boxes, dtype=np.int32)
            x_min = int(np.min(pts[:, 0]))
            y_min = int(np.min(pts[:, 1]))
            x_max = int(np.max(pts[:, 0]))
            y_max = int(np.max(pts[:, 1]))
            
            clean_text = text.strip()
            if clean_text:
                ocr_boxes.append(
                    OCRBox(
                        text=clean_text,
                        confidence=float(score),
                        bbox=[x_min, y_min, x_max, y_max],
                    )
                )

        return ocr_boxes


ocr_engine = OCREngine()
