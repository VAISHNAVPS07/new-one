from pptx import Presentation
from app.services.pptx_extractor import pptx_to_markdown

def test_extracts_slide_text(tmp_path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    box = slide.shapes.add_textbox(100, 100, 400, 100)
    box.text = "Novel sensor arrangement"
    path = tmp_path / "sample.pptx"
    prs.save(path)
    markdown = pptx_to_markdown(path)
    assert "Slide 1" in markdown
    assert "Novel sensor arrangement" in markdown
