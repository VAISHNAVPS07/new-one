"""Render an ExtractedDeck as structured Markdown, preserving slide order and references."""
from .models import ChartData, ExtractedDeck, SlideContent, TableData


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _table_md(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(_cell(c) for c in rows[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows[1:]]
    return lines


def _chart_md(chart: ChartData) -> list[str]:
    out = [f"**Chart{': ' + chart.title if chart.title else ''}** ({chart.chart_type or 'unknown type'})", ""]
    if chart.categories and chart.series:
        header = [""] + list(chart.series.keys())
        body = [[cat] + ["" if s[i] is None else str(s[i]) for s in chart.series.values()]
                for i, cat in enumerate(chart.categories)]
        out += _table_md([header] + body)
    return out


def _slide_md(slide: SlideContent, image_prefix: str) -> list[str]:
    lines = [f"## Slide {slide.number}: {slide.title or '(untitled)'}", ""]
    prev_bullet = False
    for b in slide.blocks:
        if b.is_bullet:
            lines.append("  " * b.level + f"- {b.text}")
        else:
            if prev_bullet:
                lines.append("")
            lines += [b.text, ""]
        prev_bullet = b.is_bullet
    if prev_bullet:
        lines.append("")
    for t in slide.tables:
        lines += _table_md(t.rows) + [""]
    for c in slide.charts:
        lines += _chart_md(c) + [""]
    for img in slide.images:
        lines += [f"![Slide {slide.number} image {img.index}]({image_prefix}{img.path})", ""]
        if img.description:
            lines += [f"*Diagram description (vision model, unverified): {img.description}*", ""]
        if img.ocr_text:
            lines += ["> OCR text: " + img.ocr_text.replace("\n", " "), ""]
    for w in slide.warnings:
        lines += [f"> [Extraction note] {w}", ""]
    if slide.notes:
        lines += ["**Speaker notes:**", "", slide.notes, ""]
    return lines


def render_markdown(deck: ExtractedDeck, image_prefix: str = "../") -> str:
    lines = ["# Patent Disclosure", "", f"> Source: {deck.source_file} ({deck.slide_count} slides)", ""]
    for slide in deck.slides:
        lines += _slide_md(slide, image_prefix)
    return "\n".join(lines).rstrip() + "\n"
