# OCR Backends for ClawUI

## Requirements

Choose one:

### 1. RapidOCR (Recommended, fastest)
```bash
pip install rapidocr-onnxruntime
```
- Speed: ~150ms per screenshot (CPU)
- Languages: Chinese, English, etc.
- Offline, accurate

### 2. Tesseract + Python wrapper
```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract pillow
```
- Speed: ~500ms
- Mature, but Chinese accuracy varies

---

## Usage

After installing dependencies:

```python
from src.agent import execute_tool

# Find text on screen
result = execute_tool('find_text', {'text': '新建项目'})
# Returns: {'matches': [...], 'count': N}

# Click using template (learned via learn_template.py)
execute_tool('click_template', {'app': 'wechat_devtools', 'element': '新建项目'})
```

## Notes

- `find_text` uses RapidOCR if available, falls back to Tesseract.
- Templates store relative coordinates within window; robust to window moves/resizes.
- Set DISPLAY/WAYLAND_DISPLAY for graphical environment.
