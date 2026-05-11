"""
Detects the 4x4 Word Hunt letter grid from a screenshot and OCRs each cell.

Detection strategy:
  1. Convert to HSV and mask out highly-saturated (colored) blobs — the tiles.
  2. Find contours, filter for roughly-square shapes of similar area.
  3. If we find 16 candidates arranged in a 4×4 layout, use them.
  4. Otherwise fall back to a saved calibration or prompt the user.

OCR per cell:
  - Isolate the white letter on its colored background via HSV value mask.
  - Run Tesseract in single-char mode with A-Z whitelist.
"""

import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:
    sys.exit("Missing: pip install pytesseract  (also: brew install tesseract)")

CALIBRATION_FILE = Path(__file__).parent / "calibration.json"
GRID_ROWS, GRID_COLS = 4, 4


# ---------------------------------------------------------------------------
# Grid detection
# ---------------------------------------------------------------------------

def _saturated_mask(bgr: np.ndarray) -> np.ndarray:
    """Binary mask of pixels belonging to brightly-colored tiles."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # High saturation = colored tile; exclude near-white and near-black
    mask = cv2.inRange(hsv, (0, 80, 80), (180, 255, 255))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    return mask


def _find_tile_contours(mask: np.ndarray, img_area: int) -> list[tuple]:
    """
    Return (x, y, w, h) for contours that look like letter tiles:
    roughly square, area between 0.1% and 5% of the image.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < img_area * 0.001 or area > img_area * 0.05:
            continue
        aspect = w / h if h else 0
        if not (0.6 < aspect < 1.6):
            continue
        candidates.append((x, y, w, h))
    return candidates


def _cluster_to_grid(candidates: list[tuple]) -> list[list[tuple]] | None:
    """
    Try to organise candidates into a GRID_ROWS × GRID_COLS grid sorted
    by (row, col). Returns None if the layout doesn't fit a 4×4 grid.
    """
    if len(candidates) != GRID_ROWS * GRID_COLS:
        return None

    # Sort by Y then X
    by_y = sorted(candidates, key=lambda r: r[1])
    rows = [sorted(by_y[i * GRID_COLS:(i + 1) * GRID_COLS], key=lambda r: r[0])
            for i in range(GRID_ROWS)]

    # Sanity: all cells in a row should share similar Y, all in a col similar X
    row_ys = [np.mean([r[1] for r in row]) for row in rows]
    for i in range(1, len(row_ys)):
        if row_ys[i] - row_ys[i - 1] < 5:
            return None
    return rows


def auto_detect_grid(bgr: np.ndarray) -> list[list[tuple]] | None:
    """
    Attempt to auto-detect the 4×4 grid.
    Returns a 4×4 list of (x, y, w, h) bounding boxes, or None on failure.
    """
    h, w = bgr.shape[:2]
    mask = _saturated_mask(bgr)

    # Save mask for debugging
    cv2.imwrite("debug_mask.png", mask)

    candidates = _find_tile_contours(mask, w * h)
    print(f"[grid] Tile candidates found: {len(candidates)}")

    grid = _cluster_to_grid(candidates)
    if grid is not None:
        print("[grid] Auto-detection succeeded.")
    else:
        print(
            f"[grid] Auto-detection failed (need 16 tiles, found {len(candidates)}). "
            "Run calibrate() or provide grid coordinates manually."
        )
    return grid


# ---------------------------------------------------------------------------
# Calibration fallback
# ---------------------------------------------------------------------------

def calibrate(bgr: np.ndarray) -> list[list[tuple]]:
    """
    Interactive calibration: show the screenshot and ask the user to enter
    the pixel coordinates of the top-left and bottom-right corners of the grid.
    Saves result to calibration.json.
    """
    cv2.imwrite("debug_capture.png", bgr)
    print("\n[calibrate] Saved screenshot to debug_capture.png")
    print("[calibrate] Open that image, find the 4×4 letter grid,")
    print("            and enter the pixel coordinates of its corners.\n")

    x1 = int(input("  Grid top-left  X: "))
    y1 = int(input("  Grid top-left  Y: "))
    x2 = int(input("  Grid bottom-right X: "))
    y2 = int(input("  Grid bottom-right Y: "))

    cell_w = (x2 - x1) // GRID_COLS
    cell_h = (y2 - y1) // GRID_ROWS

    grid = []
    for row in range(GRID_ROWS):
        cols = []
        for col in range(GRID_COLS):
            cx = x1 + col * cell_w
            cy = y1 + row * cell_h
            cols.append((cx, cy, cell_w, cell_h))
        grid.append(cols)

    data = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    CALIBRATION_FILE.write_text(json.dumps(data, indent=2))
    print(f"[calibrate] Saved → {CALIBRATION_FILE}")
    return grid


def load_calibration() -> list[list[tuple]] | None:
    """Load grid layout from saved calibration file, or return None."""
    if not CALIBRATION_FILE.exists():
        return None
    data = json.loads(CALIBRATION_FILE.read_text())
    x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
    cell_w = (x2 - x1) // GRID_COLS
    cell_h = (y2 - y1) // GRID_ROWS
    grid = []
    for row in range(GRID_ROWS):
        cols = []
        for col in range(GRID_COLS):
            cx = x1 + col * cell_w
            cy = y1 + row * cell_h
            cols.append((cx, cy, cell_w, cell_h))
        grid.append(cols)
    print(f"[grid] Loaded calibration from {CALIBRATION_FILE}")
    return grid


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

_TESS_CONFIG = "--psm 10 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _preprocess_cell(cell_bgr: np.ndarray) -> np.ndarray:
    """
    Extract the white letter from a colored tile.
    Returns a binary image suitable for Tesseract.
    """
    # Mask pixels with high brightness (the white letter)
    hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
    _, _, v = cv2.split(hsv)
    _, thresh = cv2.threshold(v, 180, 255, cv2.THRESH_BINARY)

    # Slight dilation so thin strokes don't break
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.dilate(thresh, kernel, iterations=1)

    # Pad and upscale for Tesseract (works best at ~32px char height)
    padded = cv2.copyMakeBorder(thresh, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=0)
    scale = max(1, 64 // padded.shape[0])
    if scale > 1:
        padded = cv2.resize(padded, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

    return padded


def ocr_cell(cell_bgr: np.ndarray) -> str:
    """OCR a single tile image and return a single uppercase letter."""
    processed = _preprocess_cell(cell_bgr)
    text = pytesseract.image_to_string(processed, config=_TESS_CONFIG).strip().upper()
    # Keep only the first alphabetic character
    for ch in text:
        if ch.isalpha():
            return ch
    return "?"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def get_grid_layout(bgr: np.ndarray) -> list[list[tuple]]:
    """
    Return the 4×4 grid layout (each cell as (x,y,w,h)).
    Tries: auto-detect → saved calibration → interactive calibration.
    """
    grid = auto_detect_grid(bgr)
    if grid is not None:
        return grid

    grid = load_calibration()
    if grid is not None:
        return grid

    return calibrate(bgr)


def parse_grid(bgr: np.ndarray, save_debug: bool = True) -> list[list[str]]:
    """
    Full pipeline: screenshot → 4×4 letter array.
    Returns e.g. [['A','B','C','D'], ['E','F','G','H'], ...]
    """
    grid_layout = get_grid_layout(bgr)

    letters: list[list[str]] = []
    debug = bgr.copy() if save_debug else None

    for row_idx, row in enumerate(grid_layout):
        letter_row = []
        for col_idx, (x, y, w, h) in enumerate(row):
            cell = bgr[y: y + h, x: x + w]
            letter = ocr_cell(cell)
            letter_row.append(letter)

            if save_debug and debug is not None:
                cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(debug, letter, (x + 4, y + h - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        letters.append(letter_row)

    if save_debug and debug is not None:
        cv2.imwrite("debug_grid.png", debug)
        print("[grid] Annotated grid saved → debug_grid.png")

    return letters


def print_grid(letters: list[list[str]]) -> None:
    print("\n+---+---+---+---+")
    for row in letters:
        print("| " + " | ".join(row) + " |")
        print("+---+---+---+---+")


if __name__ == "__main__":
    from capture import capture_phone_mirroring

    img, _ = capture_phone_mirroring()
    grid = parse_grid(img)
    print_grid(grid)
