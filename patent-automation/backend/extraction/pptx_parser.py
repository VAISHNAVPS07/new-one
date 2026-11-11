"""Extract text, bullets, tables, charts and images from a .pptx file."""
import logging
from pathlib import Path
from typing import Callable, Iterator

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.oxml.ns import qn

from .models import ChartData, ExtractedDeck, ImageRef, SlideContent, TableData, TextBlock

log = logging.getLogger(__name__)
_BODY_TYPES = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT}


def _iter_shapes(shapes) -> Iterator:
    """Yield leaf shapes in approximate reading order (top-to-bottom, left-to-right)."""
    for sh in sorted(shapes, key=lambda s: (s.top or 0, s.left or 0)):
        try:
            is_group = sh.shape_type == MSO_SHAPE_TYPE.GROUP
        except Exception:
            is_group = False
        if is_group:
            yield from _iter_shapes(sh.shapes)
        else:
            yield sh


def _is_bullet(paragraph, shape) -> bool:
    ppr = paragraph._p.pPr
    if ppr is not None:
        if ppr.find(qn("a:buNone")) is not None:
            return False
        if ppr.find(qn("a:buChar")) is not None or ppr.find(qn("a:buAutoNum")) is not None:
            return True
    try:
        return bool(shape.is_placeholder and shape.placeholder_format.type in _BODY_TYPES)
    except Exception:
        return False


def _picture_of(shape):
    """Return the image object for picture shapes / picture placeholders, else None."""
    try:
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            return shape.image
    except Exception:
        pass
    if getattr(shape, "is_placeholder", False):
        try:
            return shape.image  # PlaceholderPicture only
        except Exception:
            return None
    return None


def _chart_of(shape) -> ChartData | None:
    try:
        chart = shape.chart
        title = chart.chart_title.text_frame.text if chart.has_title else None
        plot = chart.plots[0]
        return ChartData(
            title=title,
            chart_type=str(chart.chart_type),
            categories=[str(c) for c in plot.categories],
            series={str(s.name): list(s.values) for s in plot.series},
        )
    except Exception as exc:
        log.warning("chart extraction failed: %s", exc)
        return ChartData(title="(chart could not be parsed)")


def parse_pptx(
    pptx_path: Path,
    images_dir: Path,
    job_root: Path,
    ocr: Callable[[Path], str | None] | None = None,
) -> ExtractedDeck:
    prs = Presentation(str(pptx_path))
    images_dir.mkdir(parents=True, exist_ok=True)
    slides: list[SlideContent] = []

    for number, slide in enumerate(prs.slides, start=1):
        content = SlideContent(number=number)
        title_shape = slide.shapes.title
        title_id = title_shape.shape_id if title_shape is not None else None
        if title_shape is not None and title_shape.has_text_frame:
            content.title = title_shape.text_frame.text.strip() or None

        img_index = 0
        for sh in _iter_shapes(slide.shapes):
            if title_id is not None and sh.shape_id == title_id:
                continue

            pic = _picture_of(sh)
            if pic is not None:
                img_index += 1
                fname = f"slide_{number:03d}_img_{img_index:02d}.{pic.ext}"
                out = images_dir / fname
                out.write_bytes(pic.blob)
                ref = ImageRef(slide_number=number, index=img_index, path=out.relative_to(job_root).as_posix())
                try:
                    from PIL import Image

                    with Image.open(out) as im:
                        ref.width_px, ref.height_px = im.size
                except Exception:
                    pass  # EMF/WMF etc.: kept as-is, dimensions unknown
                if ocr is not None:
                    ref.ocr_text = ocr(out)
                content.images.append(ref)
                continue

            if getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text.strip() for c in row.cells] for row in sh.table.rows]
                content.tables.append(TableData(rows=rows))
                continue

            if getattr(sh, "has_chart", False) and sh.has_chart:
                content.charts.append(_chart_of(sh))
                continue

            if "drawingml/2006/diagram" in sh._element.xml:
                content.warnings.append("SmartArt diagram present; its text/structure was not extracted.")
                continue

            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    text = p.text.replace("\x0b", " ").strip()
                    if text:
                        content.blocks.append(
                            TextBlock(text=text, level=p.level, is_bullet=_is_bullet(p, sh))
                        )
                continue

            try:
                if sh.shape_type == MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT:
                    content.warnings.append("Embedded OLE object present; content was not extracted.")
            except Exception:
                pass

        if content.title is None and content.blocks:  # no title placeholder: first line becomes the title
            content.title = content.blocks.pop(0).text

        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            content.notes = notes or None

        slides.append(content)

    return ExtractedDeck(source_file=pptx_path.name, slide_count=len(slides), slides=slides)
