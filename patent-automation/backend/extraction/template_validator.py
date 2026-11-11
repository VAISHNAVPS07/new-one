"""Data-driven validation of a deck against the corporate disclosure template."""
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator

from .models import ExtractedDeck, SlideContent

Expect = Literal["text", "bullets", "table", "image"]


class SectionSpec(BaseModel):
    id: str
    title: str
    patterns: list[str]
    required: bool = True
    expects: list[Expect] = []

    @field_validator("patterns")
    @classmethod
    def _compile_check(cls, v):
        for p in v:
            re.compile(p)
        return v


class TemplateSpec(BaseModel):
    version: int = 1
    name: str
    title_prefix_strip: str = r"^\s*slide\s*\d+\s*[:\-–.]\s*"
    sections: list[SectionSpec]

    @classmethod
    def load(cls, path: Path) -> "TemplateSpec":
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


class Issue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    slide_number: int | None = None
    section_id: str | None = None


class ValidationReport(BaseModel):
    status: Literal["pass", "warn", "fail"]
    template_name: str
    template_version: int
    slide_count: int
    matched_sections: dict[str, list[int]]
    issues: list[Issue]


_CHECKS = {
    "text": (lambda s: bool(s.blocks), "text content"),
    "bullets": (lambda s: any(b.is_bullet for b in s.blocks), "bullet points"),
    "table": (lambda s: bool(s.tables), "a table"),
    "image": (lambda s: bool(s.images), "an image or diagram"),
}


def validate_deck(deck: ExtractedDeck, spec: TemplateSpec) -> ValidationReport:
    strip_re = re.compile(spec.title_prefix_strip, re.IGNORECASE)
    compiled = {s.id: [re.compile(p, re.IGNORECASE) for p in s.patterns] for s in spec.sections}
    issues: list[Issue] = []
    matched: dict[str, list[SlideContent]] = {}

    for slide in deck.slides:
        title = re.sub(r"\s+", " ", strip_re.sub("", slide.title or "")).strip()
        if not title:
            issues.append(Issue(severity="warning", code="missing_title", slide_number=slide.number,
                                message=f"Slide {slide.number} has no title."))
        if slide.is_empty:
            issues.append(Issue(severity="warning", code="empty_slide", slide_number=slide.number,
                                message=f"Slide {slide.number} has no extractable content."))
        elif not slide.blocks and not slide.tables and not slide.charts and slide.images:
            issues.append(Issue(severity="info", code="image_only_slide", slide_number=slide.number,
                                message=f"Slide {slide.number} contains only images; its technical content "
                                        "depends on diagram analysis (OCR / vision model)."))
        for w in slide.warnings:
            issues.append(Issue(severity="warning", code="unextracted_content", slide_number=slide.number, message=w))

        hit = next((s for s in spec.sections if any(r.search(title.lower()) for r in compiled[s.id])), None)
        if hit:
            matched.setdefault(hit.id, []).append(slide)
        elif title:
            issues.append(Issue(severity="info", code="unmatched_slide", slide_number=slide.number,
                                message=f"Slide {slide.number} ('{title}') does not match any template section."))

    for section in spec.sections:
        slides = matched.get(section.id)
        if not slides:
            issues.append(Issue(
                severity="error" if section.required else "info",
                code="missing_section", section_id=section.id,
                message=f"{'Required' if section.required else 'Optional'} section '{section.title}' not found.",
            ))
            continue
        for expect in section.expects:
            check, label = _CHECKS[expect]
            if not any(check(s) for s in slides):
                issues.append(Issue(
                    severity="warning", code="incorrect_format", section_id=section.id,
                    slide_number=slides[0].number,
                    message=f"Section '{section.title}' (slide {slides[0].number}) is expected to contain {label}.",
                ))

    if any(i.severity == "error" for i in issues):
        status = "fail"
    elif any(i.severity == "warning" for i in issues):
        status = "warn"
    else:
        status = "pass"
    return ValidationReport(
        status=status, template_name=spec.name, template_version=spec.version,
        slide_count=deck.slide_count,
        matched_sections={k: [s.number for s in v] for k, v in matched.items()},
        issues=issues,
    )
