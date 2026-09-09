import pdfplumber
import json

pdf_path = "C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf"
with pdfplumber.open(pdf_path) as pdf:
    print(f"Page count: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        print("Width, Height:", page.width, page.height)
        words = page.extract_words()
        print(f"Total words: {len(words)}")
        print("Sample words (first 60):")
        for w in words[:60]:
            print(f"  {w['text']} at ({w['x0']:.1f}, {w['top']:.1f})")

        # Check curves / lines / rects
        print(f"Lines: {len(page.lines)}, Rects: {len(page.rects)}, Curves: {len(page.curves)}")
