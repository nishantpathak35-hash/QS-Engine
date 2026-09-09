"""
QS Quantification Engine — Vector PDF Primitive Extractor
Extracts vector paths, lines, rectangles, and text from PDF using pdfplumber.
Transforms PDF points to canonical millimeters (mm) with rotation handling.
Filters drawing borders, title blocks, dimension lines, and annotation markers.
Integrates WallDetector for parallel partition identification.
Enforces Blueprint Section 4 (Priority 2 — Vector PDF) & Section 15.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import math
import pdfplumber

from core.geometry.primitives import Point2D, Segment2D
from core.exceptions import ScaleRequiredError
from parsers.dxf.reader import ExtractedText
from parsers.pdf_vector.scale_calibrator import ScaleCalibrator, CalibratedScale
from semantics.walls.wall_detector import WallDetector, WallDetectionConfig


@dataclass
class ParsedPDFDrawing:
    filename: str
    page_number: int
    page_id: str
    scale: CalibratedScale
    page_width_mm: float
    page_height_mm: float
    rotation_deg: float = 0.0
    segments: list[Segment2D] = field(default_factory=list)
    texts: list[ExtractedText] = field(default_factory=list)

    def get_wall_candidates(self, wall_detector: WallDetector | None = None) -> list[Segment2D]:
        """Returns validated wall candidate segments filtered through WallDetector intelligence."""
        detector = wall_detector or WallDetector()
        return detector.validate_wall_candidates(self.segments, self.texts)


class VectorPDFExtractor:
    """Extracts geometric primitives and text from Vector PDF drawings across all pages."""

    def __init__(
        self,
        user_scale_ratio: int | None = None,
        wall_detector_config: WallDetectionConfig | None = None
    ):
        self.user_scale_ratio = user_scale_ratio
        self.wall_detector = WallDetector(config=wall_detector_config)

    def get_page_count(self, pdf_path: str | Path) -> int:
        """Returns the total number of pages in the PDF file."""
        with pdfplumber.open(str(pdf_path)) as pdf:
            return len(pdf.pages)

    def extract_page(
        self,
        pdf_path: str | Path,
        page_number: int = 1
    ) -> ParsedPDFDrawing:
        """Extracts geometry and text for a single specified page."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        with pdfplumber.open(str(path)) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                raise IndexError(f"Page {page_number} out of bounds (1-{len(pdf.pages)})")

            page = pdf.pages[page_number - 1]
            page_height_pt = float(page.height)
            page_width_pt = float(page.width)
            rotation = float(getattr(page, "rotation", 0.0) or 0.0)

            # 1. Extract text corpus to discover scale
            extracted_text_corpus = page.extract_text() or ""
            scale = ScaleCalibrator.calibrate_or_fail(
                extracted_text_corpus,
                user_scale_ratio=self.user_scale_ratio
            )
            scale_factor = scale.scale_factor_mm_per_pt
            page_w_mm = page_width_pt * scale_factor
            page_h_mm = page_height_pt * scale_factor

            # Coordinate transform: PDF top-down pt to CAD bottom-up mm with optional rotation
            def pt_to_mm(x_pt: float, y_top_pt: float) -> Point2D:
                x_raw_mm = x_pt * scale_factor
                y_raw_mm = (page_height_pt - y_top_pt) * scale_factor

                if rotation == 90.0:
                    # 90 deg clockwise rotation correction
                    return Point2D(y_raw_mm, page_w_mm - x_raw_mm)
                elif rotation == 180.0:
                    return Point2D(page_w_mm - x_raw_mm, page_h_mm - y_raw_mm)
                elif rotation == 270.0:
                    return Point2D(page_h_mm - y_raw_mm, x_raw_mm)
                return Point2D(x_raw_mm, y_raw_mm)

            segments: list[Segment2D] = []
            seg_counter = 1
            margin_threshold_mm = 20.0  # 20mm from edge is border margin

            def classify_segment_layer(p1: Point2D, p2: Point2D) -> str:
                # Detect sheet border (spans near the boundary margins)
                is_near_left = min(p1.x, p2.x) <= margin_threshold_mm
                is_near_right = max(p1.x, p2.x) >= (page_w_mm - margin_threshold_mm)
                is_near_bottom = min(p1.y, p2.y) <= margin_threshold_mm
                is_near_top = max(p1.y, p2.y) >= (page_h_mm - margin_threshold_mm)

                seg_len = p1.distance_to(p2)
                # Outer perimeter border line
                if (is_near_left and is_near_right and seg_len > 0.70 * page_w_mm) or \
                   (is_near_bottom and is_near_top and seg_len > 0.70 * page_h_mm):
                    return "PDF_BORDER"
                
                # Title block region (bottom right corner: x > 65% of width, y < 25% of height)
                if min(p1.x, p2.x) > 0.65 * page_w_mm and max(p1.y, p2.y) < 0.25 * page_h_mm:
                    return "PDF_TITLE_BLOCK"

                # Very short annotation tick or dimension line
                if seg_len < 35.0:
                    return "PDF_ANNOTATION"

                return "PDF_VECTOR"

            # 2. Extract Lines
            for line in page.lines:
                p1 = pt_to_mm(float(line["x0"]), float(line["top"]))
                p2 = pt_to_mm(float(line["x1"]), float(line["bottom"]))
                if p1.distance_to(p2) > 2.0:
                    layer = classify_segment_layer(p1, p2)
                    segments.append(Segment2D(
                        start=p1,
                        end=p2,
                        layer=layer,
                        handle=f"P{page_number}-L-{seg_counter:05d}"
                    ))
                    seg_counter += 1

            # 3. Extract Rectangles (explode into 4 boundary segments)
            for rect in page.rects:
                x0, x1 = float(rect["x0"]), float(rect["x1"])
                top, bottom = float(rect["top"]), float(rect["bottom"])
                tl = pt_to_mm(x0, top)
                tr = pt_to_mm(x1, top)
                br = pt_to_mm(x1, bottom)
                bl = pt_to_mm(x0, bottom)

                # Check if rectangle is the entire page border
                w_mm = abs(tl.x - tr.x)
                h_mm = abs(tl.y - bl.y)
                is_full_page_rect = (w_mm >= 0.85 * page_w_mm and h_mm >= 0.85 * page_h_mm)
                layer = "PDF_BORDER" if is_full_page_rect else classify_segment_layer(tl, br)

                segments.append(Segment2D(tl, tr, layer=layer, handle=f"P{page_number}-R-{seg_counter:05d}"))
                segments.append(Segment2D(tr, br, layer=layer, handle=f"P{page_number}-R-{seg_counter+1:05d}"))
                segments.append(Segment2D(br, bl, layer=layer, handle=f"P{page_number}-R-{seg_counter+2:05d}"))
                segments.append(Segment2D(bl, tl, layer=layer, handle=f"P{page_number}-R-{seg_counter+3:05d}"))
                seg_counter += 4

            # 4. Extract Text entities
            texts: list[ExtractedText] = []
            words = page.extract_words()
            for idx, w in enumerate(words):
                content = w["text"].strip()
                if not content:
                    continue
                loc = pt_to_mm(float(w["x0"]), float(w["top"]))
                texts.append(ExtractedText(
                    content=content,
                    location=loc,
                    height_mm=10.0 * scale_factor,
                    rotation_deg=rotation,
                    layer="PDF_TEXT",
                    handle=f"P{page_number}-TXT-{idx+1:04d}"
                ))

            return ParsedPDFDrawing(
                filename=path.name,
                page_number=page_number,
                page_id=f"P-{page_number}",
                scale=scale,
                page_width_mm=page_w_mm,
                page_height_mm=page_h_mm,
                rotation_deg=rotation,
                segments=segments,
                texts=texts
            )

    def extract_all_pages(self, pdf_path: str | Path) -> list[ParsedPDFDrawing]:
        """Iterates over and extracts primitives for all pages in the PDF document."""
        count = self.get_page_count(pdf_path)
        return [self.extract_page(pdf_path, page_number=p) for p in range(1, count + 1)]
