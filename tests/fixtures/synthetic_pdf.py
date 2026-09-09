"""
Synthetic Vector PDF Generator for Benchmark & Golden Testing
Generates mathematically verified Vector PDFs using reportlab with known architectural scales.
Enforces Blueprint Section 4 & Section 49.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Conversion constant: 1 mm on paper = 72 / 25.4 points
MM_TO_PT = 72.0 / 25.4

def create_synthetic_vector_pdf(output_path: str | Path) -> Path:
    """
    Creates an architectural vector PDF with 2 rooms drawn at 1:100 scale:
    1. Conference Room: 6000mm x 4000mm = 24.000 sqm (60mm x 40mm on paper)
    2. Executive Cabin: 4000mm x 4000mm = 16.000 sqm (40mm x 40mm on paper)
    Includes standard architectural scale note 'Scale: 1:100'.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    # Title & Metadata
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "ARCHITECTURAL FLOOR PLAN - LEVEL 01")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, "Scale: 1:100 | Drawing No: A-101 | Rev: 02")

    # Dimensions on paper for 1:100 scale:
    # 6m = 6000mm -> 60mm paper -> 60 * MM_TO_PT points
    # 4m = 4000mm -> 40mm paper -> 40 * MM_TO_PT points
    conf_w_pt = 60.0 * MM_TO_PT
    conf_h_pt = 40.0 * MM_TO_PT
    cabin_w_pt = 40.0 * MM_TO_PT
    cabin_h_pt = 40.0 * MM_TO_PT

    origin_x = 100.0
    origin_y = height - 250.0

    # Draw Room 1: Conference Room (6m x 4m)
    c.setLineWidth(1.5)
    c.rect(origin_x, origin_y, conf_w_pt, conf_h_pt, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(origin_x + 30, origin_y + 55, "CONFERENCE ROOM")
    c.setFont("Helvetica", 8)
    c.drawString(origin_x + 40, origin_y + 40, "24.0 SQM")
    c.drawString(origin_x + 40, origin_y + 25, "F-01")

    # Draw Room 2: Executive Cabin (4m x 4m) adjacent to Conference Room
    cabin_x = origin_x + conf_w_pt
    cabin_y = origin_y
    c.rect(cabin_x, cabin_y, cabin_w_pt, cabin_h_pt, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(cabin_x + 20, cabin_y + 55, "EXECUTIVE CABIN")
    c.setFont("Helvetica", 8)
    c.drawString(cabin_x + 30, cabin_y + 40, "16.0 SQM")
    c.drawString(cabin_x + 30, cabin_y + 25, "F-01")

    c.showPage()
    c.save()
    return path
