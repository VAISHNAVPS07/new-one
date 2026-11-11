from pathlib import Path

from backend.extraction.pptx_parser import parse_pptx
from backend.extraction.template_validator import TemplateSpec, validate_deck
from tests.conftest import ROOT, build_deck

SPEC = TemplateSpec.load(ROOT / "config/disclosure_template.yaml")


def _validate(path: Path, tmp_path):
    return validate_deck(parse_pptx(path, tmp_path / "images", tmp_path), SPEC)


def codes(report):
    return {(i.code, i.section_id) for i in report.issues}


def test_complete_deck_passes_with_info_only(deck_path, tmp_path):
    r = _validate(deck_path, tmp_path)
    assert r.status == "pass"
    assert r.matched_sections["invention_title"] == [1]  # "Slide 1:" prefix stripped
    assert r.matched_sections["architecture_diagram"] == [6]
    assert ("unmatched_slide", None) in codes(r)  # "Performance Data" is extra


def test_missing_required_section_fails(tmp_path):
    r = _validate(build_deck(tmp_path / "a.pptx", omit={"problem"}), tmp_path)
    assert r.status == "fail"
    assert ("missing_section", "problem_statement") in codes(r)


def test_wrong_format_warns(tmp_path):
    r = _validate(build_deck(tmp_path / "b.pptx", diagram_image=False), tmp_path)
    assert r.status == "warn"
    assert ("incorrect_format", "architecture_diagram") in codes(r)
