"""Annotated screenshot - overlay numbered labels on interactive elements.

Takes a screenshot and draws numbered markers on detected interactive UI elements
(buttons, inputs, links, etc.), making it easy for AI agents to reference elements
by number instead of guessing coordinates.

Supports both desktop (AT-SPI) and browser (CDP) element sources.
"""

import base64
import io
import os
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


@dataclass
class AnnotatedElement:
    """An interactive element with its label number and position."""
    index: int
    role: str
    name: str
    x: int
    y: int
    width: int
    height: int
    source: str  # "atspi", "cdp", "x11"

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "role": self.role,
            "name": self.name[:80],
            "center": list(self.center),
            "bounds": [self.x, self.y, self.width, self.height],
            "source": self.source,
        }


# Roles considered interactive
INTERACTIVE_ROLES = {
    "push button", "toggle button", "radio button", "check box",
    "menu item", "menu", "combo box", "spin button",
    "text", "password text", "entry",
    "link", "tab", "tool bar item", "slider",
    "page tab", "tree item", "list item",
}

# Minimum element size to annotate (avoid tiny/invisible elements)
MIN_SIZE = 8


def _get_atspi_elements() -> list[AnnotatedElement]:
    """Get interactive elements via single AT-SPI tree traversal."""
    elements = []
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi

        desktop = Atspi.get_desktop(0)

        def _walk(node, depth=0):
            if depth > 8:
                return
            try:
                role_name = node.get_role_name() or ""
                if role_name.lower() in INTERACTIVE_ROLES:
                    try:
                        comp = node.get_component_iface()
                        if comp:
                            ext = comp.get_extents(Atspi.CoordType.SCREEN)
                            x, y, w, h = ext.x, ext.y, ext.width, ext.height
                            if w >= MIN_SIZE and h >= MIN_SIZE and x >= 0 and y >= 0:
                                name = node.get_name() or ""
                                # Check visibility via states
                                state_set = node.get_state_set()
                                if state_set and (state_set.contains(Atspi.StateType.VISIBLE) or
                                                  state_set.contains(Atspi.StateType.SHOWING)):
                                    elements.append(AnnotatedElement(
                                        index=0, role=role_name, name=name,
                                        x=x, y=y, width=w, height=h, source="atspi",
                                    ))
                    except Exception:
                        pass
                count = node.get_child_count()
                for i in range(count):
                    child = node.get_child_at_index(i)
                    if child:
                        _walk(child, depth + 1)
            except Exception:
                pass

        count = desktop.get_child_count()
        for i in range(count):
            app = desktop.get_child_at_index(i)
            if app:
                _walk(app, 0)
    except Exception:
        pass
    return elements


def _get_cdp_elements() -> list[AnnotatedElement]:
    """Get interactive elements from browser via CDP."""
    elements = []
    try:
        from .cdp_helper import get_or_create_cdp_client
        cdp = get_or_create_cdp_client()
        if not cdp or not cdp.is_available():
            return elements

        # Get all interactive elements with bounding boxes
        js = """
        (function() {
            const selectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="checkbox"], [role="radio"], [onclick], [tabindex]';
            const els = document.querySelectorAll(selectors);
            const results = [];
            for (const el of els) {
                if (el.offsetParent === null && el.tagName !== 'BODY') continue;
                const rect = el.getBoundingClientRect();
                if (rect.width < 8 || rect.height < 8) continue;
                if (rect.top > window.innerHeight || rect.left > window.innerWidth) continue;
                if (rect.bottom < 0 || rect.right < 0) continue;
                const text = (el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '').trim().substring(0, 80);
                const role = el.getAttribute('role') || el.tagName.toLowerCase();
                results.push({
                    role: role,
                    name: text,
                    x: Math.round(rect.left),
                    y: Math.round(rect.top),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                });
                if (results.length >= 150) break;
            }
            return results;
        })()
        """
        result = cdp.evaluate(js)
        items = result.get("result", {}).get("value", [])
        if isinstance(items, list):
            for item in items:
                elements.append(AnnotatedElement(
                    index=0,
                    role=item.get("role", "unknown"),
                    name=item.get("name", ""),
                    x=item.get("x", 0),
                    y=item.get("y", 0),
                    width=item.get("w", 0),
                    height=item.get("h", 0),
                    source="cdp",
                ))
    except Exception:
        pass
    return elements


def _deduplicate(elements: list[AnnotatedElement], threshold: int = 20) -> list[AnnotatedElement]:
    """Remove near-duplicate elements (same position within threshold pixels)."""
    unique = []
    for el in elements:
        cx, cy = el.center
        is_dup = False
        for existing in unique:
            ex, ey = existing.center
            if abs(cx - ex) < threshold and abs(cy - ey) < threshold:
                # Keep the one with more info (longer name or atspi preferred)
                if len(el.name) > len(existing.name):
                    unique.remove(existing)
                    unique.append(el)
                is_dup = True
                break
        if not is_dup:
            unique.append(el)
    return unique


def _draw_annotations(
    img: Image.Image,
    elements: list[AnnotatedElement],
    label_size: int = 16,
) -> Image.Image:
    """Draw numbered labels on the image at element positions."""
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Try to get a font
    font = None
    font_size = max(label_size, 12)
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue
    if not font:
        font = ImageFont.load_default()

    for el in elements:
        cx, cy = el.center
        label = str(el.index)
        
        # Calculate label dimensions
        bbox = font.getbbox(label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        padding = 3
        
        # Position label at top-left of element, offset slightly
        lx = max(0, el.x - 2)
        ly = max(0, el.y - th - padding * 2 - 2)
        
        # If label would be off-screen top, place it inside
        if ly < 0:
            ly = el.y + 2
        
        # Draw element highlight rectangle (semi-transparent)
        draw.rectangle(
            [el.x, el.y, el.x + el.width, el.y + el.height],
            outline=(255, 0, 0, 180),
            width=2,
        )
        
        # Draw label background (red pill)
        draw.rectangle(
            [lx, ly, lx + tw + padding * 2, ly + th + padding * 2],
            fill=(220, 30, 30, 230),
        )
        
        # Draw label text (white)
        draw.text((lx + padding, ly + padding), label, fill=(255, 255, 255, 255), font=font)

    return img


def take_annotated_screenshot(
    source: str = "auto",
    max_elements: int = 80,
) -> tuple[str, list[dict]]:
    """
    Take a screenshot with numbered annotations on interactive elements.
    
    Args:
        source: "atspi", "cdp", or "auto" (try both)
        max_elements: Maximum number of elements to annotate
        
    Returns:
        Tuple of (base64_png, element_list) where element_list contains
        dicts with index, role, name, center, bounds for each annotated element.
    """
    from .screenshot import take_screenshot
    
    # Get raw screenshot
    raw_b64 = take_screenshot(scale=False)
    img = Image.open(io.BytesIO(base64.b64decode(raw_b64)))
    
    # Collect elements
    elements: list[AnnotatedElement] = []
    
    if source in ("auto", "atspi"):
        elements.extend(_get_atspi_elements())
    if source in ("auto", "cdp"):
        elements.extend(_get_cdp_elements())
    
    # Deduplicate and limit
    elements = _deduplicate(elements)
    
    # Sort by position (top-to-bottom, left-to-right) for consistent numbering
    elements.sort(key=lambda e: (e.y // 40, e.x))  # Group by ~40px rows
    
    # Assign indices and limit
    for i, el in enumerate(elements[:max_elements]):
        el.index = i + 1
    elements = elements[:max_elements]
    
    # Draw annotations
    annotated_img = _draw_annotations(img, elements)
    
    # Scale down for AI processing
    max_w, max_h = 1366, 768
    if annotated_img.width > max_w or annotated_img.height > max_h:
        ratio = min(max_w / annotated_img.width, max_h / annotated_img.height)
        new_size = (int(annotated_img.width * ratio), int(annotated_img.height * ratio))
        annotated_img = annotated_img.resize(new_size, Image.LANCZOS)
    
    # Encode
    buf = io.BytesIO()
    annotated_img.save(buf, format='PNG', optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    # Build element list
    element_list = [el.to_dict() for el in elements]
    
    return b64, element_list
