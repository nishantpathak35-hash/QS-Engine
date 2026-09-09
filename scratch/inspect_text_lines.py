import pdfplumber
import json
from pathlib import Path

pdf_path = "C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    page = pdf.pages[0]
    print(f"Page dimensions: {page.width} x {page.height} pt")
    
    words = page.extract_words()
    print(f"\nTotal extracted words: {len(words)}")
    
    # Sort words by y (top to bottom), then x (left to right)
    words_sorted = sorted(words, key=lambda w: (round(w['top'], -1), w['x0']))
    
    # Group into lines of text
    lines = []
    curr_line = []
    curr_y = None
    for w in words_sorted:
        if curr_y is None or abs(w['top'] - curr_y) > 4:
            if curr_line:
                lines.append(" ".join(cw['text'] for cw in curr_line))
            curr_line = [w]
            curr_y = w['top']
        else:
            curr_line.append(w)
    if curr_line:
        lines.append(" ".join(cw['text'] for cw in curr_line))
        
    print("\n--- RECONSTRUCTED TEXT LINES ---")
    for l in lines:
        print(l)
        
    print("\n--- DRAWING OBJECT COUNTS ---")
    print(f"Lines: {len(page.lines)}")
    print(f"Rects: {len(page.rects)}")
    print(f"Curves: {len(page.curves)}")
    print(f"Images: {len(page.images)}")
