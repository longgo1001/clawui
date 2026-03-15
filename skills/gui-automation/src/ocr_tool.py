"""OCR-based UI text detection tool for ClawUI.

Primary: RapidOCR (fastest, ~150ms)
Fallback: Tesseract (slower but universal)
Supports exact substring and fuzzy matching for resilient text finding.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("clawui.ocr_tool")

# Add current module path
sys.path.insert(0, os.path.dirname(__file__))


# Initialize OCR engine at module import (singleton)
try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
    _has_rapidocr = True
except ImportError:
    _ocr_engine = None
    _has_rapidocr = False

def _decode_image_bytes(image_data: str) -> bytes:
    """Decode base64 image payload (supports optional data: URI prefix)."""
    import base64
    if image_data.startswith('data:'):
        _, b64 = image_data.split(',', 1)
        return base64.b64decode(b64)
    return base64.b64decode(image_data)


def ocr_extract_lines(image_data: str, threshold: float = 0.0) -> List[Dict[str, Any]]:
    """
    Extract all OCR lines from screenshot.
    Returns list: [{text, bbox, center, score}]
    """
    lines: List[Dict[str, Any]] = []

    # RapidOCR path
    if _has_rapidocr and _ocr_engine is not None:
        try:
            image_bytes = _decode_image_bytes(image_data)
            result, _ = _ocr_engine(image_bytes)
            if result:
                for box, ocr_text, score in result:
                    if score < threshold:
                        continue
                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]
                    center = [int(sum(xs) / len(xs)), int(sum(ys) / len(ys))]
                    lines.append({
                        "text": ocr_text,
                        "bbox": box,
                        "center": center,
                        "score": float(score)
                    })
            return lines
        except Exception as e:
            print(f"[ocr_extract_lines] RapidOCR failed: {e}")

    # Tesseract fallback
    try:
        import subprocess
        import tempfile
        image_bytes = _decode_image_bytes(image_data)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        cmd = ['tesseract', tmp_path, 'stdout', '--psm', '11', 'tsv']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        os.unlink(tmp_path)
        if result.returncode != 0:
            raise RuntimeError(f"Tesseract error: {result.stderr}")

        import csv
        rows = result.stdout.strip().split('\n')
        reader = csv.DictReader(rows, delimiter='\t')
        for row in reader:
            text = row.get('text', '')
            if not text:
                continue
            x, y = int(row['left']), int(row['top'])
            w, h = int(row['width']), int(row['height'])
            lines.append({
                "text": text,
                "bbox": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                "center": [int(x + w / 2), int(y + h / 2)],
                "score": 0.5
            })
        return lines
    except Exception as e:
        print(f"[ocr_extract_lines] Tesseract failed: {e}")
        return []


def _fuzzy_match(needle: str, haystack: str, max_distance: int = 2) -> bool:
    """Check if needle approximately matches haystack using edit distance.

    Supports substring fuzzy matching: returns True if any substring of
    haystack of length close to needle has edit distance <= max_distance.
    This handles common OCR errors like 'O' vs '0', 'l' vs '1', etc.
    """
    needle_lower = needle.lower()
    haystack_lower = haystack.lower()

    # Exact substring check first (fast path)
    if needle_lower in haystack_lower:
        return True

    if max_distance <= 0:
        return False

    # Simple Levenshtein for short strings
    n_len = len(needle_lower)
    h_len = len(haystack_lower)

    if n_len == 0:
        return True
    if h_len == 0:
        return False

    # For short needles, check full-string distance
    if n_len <= 3:
        return _levenshtein(needle_lower, haystack_lower) <= max_distance

    # Sliding window: check substrings of haystack close to needle length
    window = n_len + max_distance
    for i in range(max(1, h_len - window + 1)):
        sub = haystack_lower[i:i + window]
        if _levenshtein(needle_lower, sub) <= max_distance:
            return True

    return False


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,        # insert
                prev_row[j + 1] + 1,    # delete
                prev_row[j] + cost      # substitute
            ))
        prev_row = curr_row
    return prev_row[-1]


def ocr_find_text(
    image_data: str,
    text: str,
    threshold: float = 0.3,
    fuzzy: bool = False,
    max_edit_distance: int = 2,
) -> List[Dict[str, Any]]:
    """
    Find occurrences of `text` in screenshot via OCR.
    Returns list of matches: [{text, bbox: [[x1,y1],[x2,y2],...], center: [x,y], score}]

    Args:
        image_data: Base64-encoded image (with or without data: URI prefix).
        text: Text to search for (case-insensitive substring match).
        threshold: Minimum OCR confidence score (default 0.3).
        fuzzy: Enable fuzzy matching to tolerate OCR errors (e.g. 'O'/'0').
        max_edit_distance: Max Levenshtein distance for fuzzy matching (default 2).

    Uses ocr_extract_lines internally — no duplicated OCR logic.
    """
    all_lines = ocr_extract_lines(image_data, threshold=threshold)
    matches = []

    for line in all_lines:
        ocr_text = line.get("text", "")
        if fuzzy:
            if _fuzzy_match(text, ocr_text, max_edit_distance):
                matches.append(line)
        else:
            if text.lower() in ocr_text.lower():
                matches.append(line)

    return matches


# Standalone test
if __name__ == "__main__":
    # Take a screenshot and search for text
    from clawui.screenshot import take_screenshot
    img = take_screenshot()
    if img:
        import base64
        b64 = base64.b64decode(img) if isinstance(img, str) else img
        matches = ocr_find_text(base64.b64encode(b64).decode(), "新建")
        print(f"Found {len(matches)} matches for '新建':")
        for m in matches:
            print(f"  {m['text']} at {m['center']} (score {m['score']:.2f})")
