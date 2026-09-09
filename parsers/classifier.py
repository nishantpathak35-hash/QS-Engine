"""
QS Quantification Engine — Drawing Type Classifier
Inspects input files and classifies them as DXF, Vector PDF, Mixed PDF, or Raster PDF.
Enforces Blueprint Section 8 (Module 2 — Drawing Type Classifier).
"""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
import pdfplumber

class DrawingType(str, Enum):
    DXF = "dxf"
    VECTOR_PDF = "vector_pdf"
    MIXED_PDF = "mixed_pdf"
    RASTER_PDF = "raster_pdf"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


@dataclass
class PageClassification:
    page_number: int
    drawing_type: DrawingType
    vector_path_count: int
    char_count: int
    image_count: int
    confidence: float


@dataclass
class DrawingClassificationResult:
    filename: str
    overall_type: DrawingType
    page_count: int
    pages: list[PageClassification]


class DrawingTypeClassifier:
    """Classifies architectural drawings to route them to the appropriate ingestion pipeline."""

    @staticmethod
    def classify_file(file_path: str | Path) -> DrawingClassificationResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()

        # 1. DXF Check
        if ext == ".dxf":
            page_info = PageClassification(
                page_number=1,
                drawing_type=DrawingType.DXF,
                vector_path_count=0,
                char_count=0,
                image_count=0,
                confidence=0.99
            )
            return DrawingClassificationResult(
                filename=path.name,
                overall_type=DrawingType.DXF,
                page_count=1,
                pages=[page_info]
            )

        # 2. PDF Check
        if ext == ".pdf":
            return DrawingTypeClassifier._classify_pdf(path)

        # 3. Image Check
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            page_info = PageClassification(
                page_number=1,
                drawing_type=DrawingType.IMAGE,
                vector_path_count=0,
                char_count=0,
                image_count=1,
                confidence=0.95
            )
            return DrawingClassificationResult(
                filename=path.name,
                overall_type=DrawingType.IMAGE,
                page_count=1,
                pages=[page_info]
            )

        return DrawingClassificationResult(
            filename=path.name,
            overall_type=DrawingType.UNSUPPORTED,
            page_count=0,
            pages=[]
        )

    @staticmethod
    def _classify_pdf(pdf_path: Path) -> DrawingClassificationResult:
        pages: list[PageClassification] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages):
                vector_count = len(page.lines) + len(page.curves) + len(page.rects)
                text = page.extract_text() or ""
                char_count = len(text.strip())
                image_count = len(page.images)

                # Determine page type
                if vector_count > 5:
                    if image_count > 0 and char_count == 0:
                        ptype = DrawingType.MIXED_PDF
                        conf = 0.85
                    else:
                        ptype = DrawingType.VECTOR_PDF
                        conf = 0.95
                elif image_count > 0:
                    ptype = DrawingType.RASTER_PDF
                    conf = 0.90
                else:
                    ptype = DrawingType.VECTOR_PDF if char_count > 0 else DrawingType.UNSUPPORTED
                    conf = 0.70

                pages.append(PageClassification(
                    page_number=idx + 1,
                    drawing_type=ptype,
                    vector_path_count=vector_count,
                    char_count=char_count,
                    image_count=image_count,
                    confidence=conf
                ))

        # Overall type logic: if any page is vector, treat as Vector/Mixed
        overall = pages[0].drawing_type if pages else DrawingType.UNSUPPORTED
        if any(p.drawing_type == DrawingType.VECTOR_PDF for p in pages):
            overall = DrawingType.VECTOR_PDF

        return DrawingClassificationResult(
            filename=pdf_path.name,
            overall_type=overall,
            page_count=len(pages),
            pages=pages
        )
