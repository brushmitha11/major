import cv2
import numpy as np


def _square_cells(region, w_full, h_full):
    _, binary = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    return [b for b in boxes if 0.02 * h_full <= b[3] <= 0.09 * h_full
            and 0.012 * w_full <= b[2] <= 0.04 * w_full and 0.7 <= b[2] / b[3] <= 1.3]


def find_date_strip(gray):
    h, w = gray.shape[:2]
    region = gray[0:int(h * 0.45), int(w * 0.45):]
    cells = _square_cells(region, w, h)
    best = None
    for _, y, _, bh in cells:
        row = sorted([c for c in cells if abs(c[1] - y) < 0.3 * bh], key=lambda c: c[0])
        if len(row) >= 4 and (best is None or len(row) > len(best)):
            best = row
    if best is None:
        return None
    pitch = float(np.median(np.diff([c[0] for c in best])))
    cell_w = float(np.median([c[2] for c in best]))
    top = int(np.median([c[1] for c in best]))
    cell_h = int(np.median([c[3] for c in best]))
    right = best[-1][0] + int(cell_w)
    left = int(right - 8 * pitch)
    if left < 0 or pitch < 0.8 * cell_w:
        return None
    return region[top:top + cell_h, max(0, left):right]
