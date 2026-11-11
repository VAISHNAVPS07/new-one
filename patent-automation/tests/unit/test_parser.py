from backend.extraction.pptx_parser import parse_pptx


def test_parse_structure(deck_path, tmp_path):
    root = tmp_path / "job"
    deck = parse_pptx(deck_path, root / "images", root)
    assert deck.slide_count == 7
    assert [s.title for s in deck.slides][:2] == ["Slide 1: Invention Title", "Problem Statement"]

    comp = deck.slides[3]
    assert [b.text for b in comp.blocks] == ["Temperature sensors", "Airflow control unit", "PWM driver", "Cooling mechanism"]
    assert all(b.is_bullet for b in comp.blocks)
    assert comp.blocks[2].level == 1

    subtitle = deck.slides[0].blocks[0]
    assert subtitle.text == "Intelligent Thermal Management System" and not subtitle.is_bullet


def test_images_tables_notes(deck_path, tmp_path):
    root = tmp_path / "job"
    deck = parse_pptx(deck_path, root / "images", root)
    img = deck.slides[5].images[0]
    assert (root / img.path).exists() and img.width_px == 120
    assert deck.slides[6].tables[0].rows[1] == ["Cooling gain", "12 | 15 %"]
    assert deck.slides[6].notes == "Synthetic benchmark numbers."
