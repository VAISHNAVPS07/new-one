from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    text: str
    level: int = 0
    is_bullet: bool = False


class TableData(BaseModel):
    rows: list[list[str]]


class ChartData(BaseModel):
    title: str | None = None
    chart_type: str | None = None
    categories: list[str] = []
    series: dict[str, list[float | None]] = {}


class ImageRef(BaseModel):
    slide_number: int
    index: int
    path: str  # relative to the job workspace root, e.g. images/slide_004_img_01.png
    width_px: int | None = None
    height_px: int | None = None
    ocr_text: str | None = None
    description: str | None = None  # filled later by an approved vision LLM (optional)


class SlideContent(BaseModel):
    number: int
    title: str | None = None
    blocks: list[TextBlock] = []
    tables: list[TableData] = []
    charts: list[ChartData] = []
    images: list[ImageRef] = []
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)  # content we could not extract (e.g. SmartArt)

    @property
    def is_empty(self) -> bool:
        return not (self.blocks or self.tables or self.charts or self.images)


class ExtractedDeck(BaseModel):
    source_file: str
    slide_count: int
    slides: list[SlideContent]
