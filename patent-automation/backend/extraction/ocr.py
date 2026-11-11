"""Optional OCR. Disabled by default; enable with PATENT_OCR_ENABLED=true.

Requires `pip install pytesseract` and the tesseract binary. If either is missing
we return None instead of failing the whole extraction.
"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run_ocr(image_path: Path) -> str | None:
    try:
        import pytesseract
        from PIL import Image

        with Image.open(image_path) as im:
            text = pytesseract.image_to_string(im).strip()
        return text or None
    except Exception as exc:  # missing lib/binary, unsupported format (e.g. EMF/WMF)
        log.warning("OCR skipped for %s: %s", image_path.name, exc)
        return None
