"""Fixtures build SYNTHETIC test decks programmatically (not real disclosures)."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from backend.core.config import Settings
from backend.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def build_deck(path: Path, omit: set[str] = frozenset(), diagram_image: bool = True) -> Path:
    prs = Presentation()

    def content(title, items):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        tf = s.placeholders[1].text_frame
        tf.text = items[0]
        for it in items[1:]:
            lvl = 0
            if it.startswith("  "):
                lvl, it = 1, it.strip()
            p = tf.add_paragraph()
            p.text, p.level = it, lvl
        return s

    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "Slide 1: Invention Title"
    s.placeholders[1].text = "Intelligent Thermal Management System"
    if "problem" not in omit:
        content("Problem Statement", ["Existing thermal management systems have inefficient heat distribution."])
    content("Proposed Solution", ["An adaptive cooling mechanism that adjusts airflow based on temperature."])
    content("Key Components", ["Temperature sensors", "Airflow control unit", "  PWM driver", "Cooling mechanism"])
    content("Technical Advantages", ["Improved cooling efficiency", "Reduced energy consumption"])

    d = prs.slides.add_slide(prs.slide_layouts[5])
    d.shapes.title.text = "System Architecture Diagram"
    if diagram_image:
        buf = io.BytesIO()
        Image.new("RGB", (120, 80), "steelblue").save(buf, "PNG")
        buf.seek(0)
        d.shapes.add_picture(buf, Inches(1), Inches(2), Inches(4))

    t = prs.slides.add_slide(prs.slide_layouts[5])
    t.shapes.title.text = "Performance Data"
    tbl = t.shapes.add_table(3, 2, Inches(1), Inches(2), Inches(6), Inches(1.5)).table
    for r, row in enumerate([["Metric", "Value"], ["Cooling gain", "12 | 15 %"], ["Power", "-8 %"]]):
        for c, val in enumerate(row):
            tbl.cell(r, c).text = val
    prs.slides[-1].notes_slide.notes_text_frame.text = "Synthetic benchmark numbers."
    prs.save(path)
    return path


@pytest.fixture
def deck_path(tmp_path):
    return build_deck(tmp_path / "sample.pptx")


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=tmp_path / "jobs", template_config=ROOT / "config/disclosure_template.yaml")


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings))
