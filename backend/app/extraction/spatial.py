from typing import List, Optional, Tuple
from ..schemas.invoice import OCRBox


def calculate_vertical_overlap(box1: OCRBox, box2: OCRBox) -> float:
    """Calculates vertical intersection over the height of box1."""
    _, y1_min, _, y1_max = box1.bbox
    _, y2_min, _, y2_max = box2.bbox
    
    overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    h1 = max(1, y1_max - y1_min)
    return overlap / h1


def find_box_to_right(
    target_box: OCRBox,
    all_boxes: List[OCRBox],
    max_horizontal_gap: int = 600,
    min_vertical_overlap: float = 0.4,
) -> Optional[OCRBox]:
    """Finds the closest OCR box directly to the right on the same line."""
    x1_min, y1_min, x1_max, y1_max = target_box.bbox
    target_cy = (y1_min + y1_max) / 2.0
    
    best_candidate: Optional[OCRBox] = None
    min_distance = float("inf")
    
    for box in all_boxes:
        if box == target_box:
            continue
        x2_min, y2_min, x2_max, y2_max = box.bbox
        
        # Must be to the right
        if x2_min >= x1_min:
            gap = x2_min - x1_max
            if 0 <= gap <= max_horizontal_gap:
                v_overlap = calculate_vertical_overlap(target_box, box)
                box_cy = (y2_min + y2_max) / 2.0
                y_diff = abs(target_cy - box_cy)
                
                if v_overlap >= min_vertical_overlap or y_diff < (y1_max - y1_min):
                    distance = gap + (y_diff * 2)
                    if distance < min_distance:
                        min_distance = distance
                        best_candidate = box
                        
    return best_candidate


def find_box_below(
    target_box: OCRBox,
    all_boxes: List[OCRBox],
    max_vertical_gap: int = 200,
) -> Optional[OCRBox]:
    """Finds the closest OCR box directly below the target box with horizontal alignment."""
    x1_min, y1_min, x1_max, y1_max = target_box.bbox
    target_cx = (x1_min + x1_max) / 2.0
    
    best_candidate: Optional[OCRBox] = None
    min_distance = float("inf")
    
    for box in all_boxes:
        if box == target_box:
            continue
        x2_min, y2_min, x2_max, y2_max = box.bbox
        
        # Must be below
        if y2_min >= y1_min:
            gap = y2_min - y1_max
            if 0 <= gap <= max_vertical_gap:
                box_cx = (x2_min + x2_max) / 2.0
                x_diff = abs(target_cx - box_cx)
                
                # Check horizontal alignment
                h_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
                if h_overlap > 0 or x_diff < (x1_max - x1_min):
                    distance = gap + x_diff
                    if distance < min_distance:
                        min_distance = distance
                        best_candidate = box
                        
    return best_candidate
