"""OCR-based UI text detection tool for ClawUI.

Primary: RapidOCR (fastest, ~150ms)
Fallback: Tesseract (slower but universal)
"""

import os
import sys
from typing import List, Dict, Any

# Add current module path
sys.path.insert(0, os.path.dirname(__file__))


def ocr_find_text(image_data: str, text: str, threshold: float = 0.6) -> List[Dict[str, Any]]:
    """
    Find occurrences of `text` in screenshot via OCR.
    Returns list of matches: [{text, bbox: [[x1,y1],[x2,y2],...], center: [x,y], score}]
    """
    # Try RapidOCR first
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        # image_data is base64 string without data: prefix
        if image_data.startswith('data:'):
            import base64
            header, b64 = image_data.split(',', 1)
            image_bytes = base64.b64decode(b64)
        else:
            import base64
            image_bytes = base64.b64decode(image_data)
        
        result = ocr(image_bytes)
        # result format: (bboxes, scores, texts)
        matches = []
        if result:
            bboxes, scores, texts = result
            for box, score, ocr_text in zip(bboxes, scores, texts):
                if text.lower() in ocr_text.lower():
                    # Compute center
                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]
                    center = [int(sum(xs)/len(xs)), int(sum(ys)/len(ys))]
                    matches.append({
                        "text": ocr_text,
                        "bbox": box.tolist() if hasattr(box, 'tolist') else box,
                        "center": center,
                        "score": float(score)
                    })
        return matches
    except Exception as e:
        print(f"[ocr_find_text] RapidOCR failed: {e}")
        pass

    # Fallback to Tesseract
    try:
        import subprocess
        import tempfile
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_bytes if 'image_bytes' in locals() else 
                     (base64.b64decode(image_data.split(',',1)[1] if ',' in image_data else image_data)))
            tmp_path = tmp.name
        
        # Run tesseract with TSV output
        cmd = ['tesseract', tmp_path, 'stdout', '--psm', '11', 'tsv']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        os.unlink(tmp_path)
        
        if result.returncode != 0:
            raise RuntimeError(f"Tesseract error: {result.stderr}")
        
        lines = result.stdout.strip().split('\n')
        matches = []
        import csv
        reader = csv.DictReader(lines, delimiter='\t')
        for row in reader:
            if 'text' in row and 'left' in row:
                if text.lower() in row['text'].lower():
                    x = int(row['left']) + int(row['width'])/2
                    y = int(row['top']) + int(row['height'])/2
                    matches.append({
                        "text": row['text'],
                        "bbox": [[int(row['left']), int(row['top'])],
                                 [int(row['left'])+int(row['width']), int(row['top'])],
                                 [int(row['left'])+int(row['width']), int(row['top'])+int(row['height'])],
                                 [int(row['left']), int(row['top'])+int(row['height'])]],
                        "center": [int(x), int(y)],
                        "score": 0.5  # Tesseract has no confidence
                    })
        return matches
    except Exception as e:
        print(f"[ocr_find_text] Tesseract failed: {e}")
        return []


# Standalone test
if __name__ == "__main__":
    # Take a screenshot and search for text
    from src.screenshot import take_screenshot
    img = take_screenshot()
    if img:
        import base64
        b64 = base64.b64decode(img) if isinstance(img, str) else img
        matches = ocr_find_text(base64.b64encode(b64).decode(), "新建")
        print(f"Found {len(matches)} matches for '新建':")
        for m in matches:
            print(f"  {m['text']} at {m['center']} (score {m['score']:.2f})")
