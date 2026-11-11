from pathlib import Path
from pptx import Presentation

def pptx_to_markdown(path: Path) -> str:
    prs = Presentation(str(path))
    sections = [f"# Patent disclosure: {path.name}", ""]
    for slide_no, slide in enumerate(prs.slides, start=1):
        sections += [f"## Slide {slide_no}", ""]
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text.strip():
                sections.append(shape.text.strip())
                sections.append("")
            if getattr(shape, "has_table", False):
                table = shape.table
                rows = []
                for row in table.rows:
                    rows.append([cell.text.replace("|", r"\|").replace("\n", " ").strip()
                                 for cell in row.cells])
                if rows:
                    sections.append("| " + " | ".join(rows[0]) + " |")
                    sections.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
                    for row in rows[1:]:
                        sections.append("| " + " | ".join(row) + " |")
                    sections.append("")
    return "\n".join(sections).strip() + "\n"
