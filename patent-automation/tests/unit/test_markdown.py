from backend.extraction.markdown_writer import render_markdown
from backend.extraction.pptx_parser import parse_pptx


def test_markdown_output(deck_path, tmp_path):
    md = render_markdown(parse_pptx(deck_path, tmp_path / "images", tmp_path))
    assert md.startswith("# Patent Disclosure")
    assert "## Slide 4: Key Components" in md
    assert "- Temperature sensors" in md and "  - PWM driver" in md
    assert "![Slide 6 image 1](../images/slide_006_img_01.png)" in md
    assert "| Metric | Value |" in md and "12 \\| 15 %" in md  # pipe escaped
    assert "**Speaker notes:**" in md
    order = [md.index(f"## Slide {n}:") for n in range(1, 8)]
    assert order == sorted(order)
