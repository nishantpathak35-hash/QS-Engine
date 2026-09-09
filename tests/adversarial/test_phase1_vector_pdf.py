"""
Adversarial Tests — Phase-1 Vector PDF Pipeline
Validates:
1. Multi-page extraction with page_id and entity isolation.
2. Page-level scale resolution: missing scale raises ScaleRequiredError.
3. Drawing border exclusion from wall candidates.
4. Scale override capability.
"""

import pytest
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from parsers.pdf_vector.extractor import VectorPDFExtractor
from core.exceptions import ScaleRequiredError


def test_multipage_pdf_extraction(tmp_path: Path):
    """Multi-page PDF must extract all pages with distinct page IDs."""
    pdf_path = tmp_path / "multipage_drawing.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # Page 1
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 50, "Scale: 1:100 | Page 1")
    c.rect(100, 100, 200, 150)
    c.showPage()

    # Page 2
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 50, "Scale: 1:50 | Page 2")
    c.rect(120, 120, 180, 140)
    c.showPage()

    c.save()

    extractor = VectorPDFExtractor()
    assert extractor.get_page_count(pdf_path) == 2

    pages = extractor.extract_all_pages(pdf_path)
    assert len(pages) == 2
    assert pages[0].page_id == "P-1"
    assert pages[0].scale.ratio_string == "1:100"
    assert pages[1].page_id == "P-2"
    assert pages[1].scale.ratio_string == "1:50"


def test_pdf_without_scale_raises_scale_required(tmp_path: Path):
    """Vector PDF with no detectable scale note and no override must raise ScaleRequiredError."""
    pdf_path = tmp_path / "unscaled_drawing.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(50, 700, "UNSCALED SKETCH PLAN (NO SCALE NOTE)")
    c.rect(100, 100, 200, 200)
    c.save()

    extractor = VectorPDFExtractor()
    with pytest.raises(ScaleRequiredError):
        extractor.extract_page(pdf_path, page_number=1)


def test_pdf_user_scale_override_succeeds(tmp_path: Path):
    """Vector PDF without scale note succeeds when user_scale_ratio=100 is provided."""
    pdf_path = tmp_path / "unscaled_drawing.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(50, 700, "UNSCALED SKETCH PLAN")
    c.rect(100, 100, 200, 200)
    c.save()

    extractor = VectorPDFExtractor(user_scale_ratio=100)
    parsed = extractor.extract_page(pdf_path, page_number=1)
    assert parsed.scale.ratio_string == "1:100"
    assert parsed.scale.source == "user_calibration"


def test_drawing_border_is_excluded_from_wall_candidates(tmp_path: Path):
    """Full-page border rectangles must be tagged PDF_BORDER and excluded from wall candidates."""
    pdf_path = tmp_path / "sheet_with_border.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # Scale note
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 30, "Scale: 1:100")

    # Sheet outer border (spans entire page)
    c.rect(10, 10, width - 20, height - 20)

    # Interior room wall
    c.rect(150, 200, 100, 80)
    c.save()

    extractor = VectorPDFExtractor()
    parsed = extractor.extract_page(pdf_path, page_number=1)

    border_segs = [s for s in parsed.segments if s.layer == "PDF_BORDER"]
    assert len(border_segs) > 0, "Outer page rectangle must be classified as PDF_BORDER!"

    wall_candidates = parsed.get_wall_candidates()
    assert all(s.layer != "PDF_BORDER" for s in wall_candidates)
