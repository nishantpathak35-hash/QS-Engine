import pdfplumber
import math

pdf_path = "C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    
    # Let's find pairs of dimension numbers and their positions
    # For example, 450, 900, 900, 900 along the top or bottom
    dim_words = [w for w in words if w['text'] in ('450', '900', '600', '1350', '2060', '1490', '2440', '1015', '1025', '1580', '2810', '1525', '6755')]
    print(f"Found {len(dim_words)} dimension words.")
    for dw in dim_words:
        print(f"  {dw['text']:>5} at ({dw['x0']:6.1f}, {dw['top']:6.1f})")

    # Let's measure the distance between consecutive 900s at the top
    top_900s = sorted([w for w in words if w['text'] == '900' and w['top'] < 70], key=lambda w: w['x0'])
    print(f"\nTop 900s count: {len(top_900s)}")
    for i in range(len(top_900s)-1):
        dx_pt = top_900s[i+1]['x0'] - top_900s[i]['x0']
        ratio = 900.0 / dx_pt  # mm per pt
        # If scale is 1:S, then 1 pt = (1/72) inch = 25.4/72 mm = 0.352778 mm on paper.
        # So drawing scale S = ratio / 0.352778
        scale_S = ratio / (25.4 / 72.0)
        print(f"  dx_pt={dx_pt:.2f} pt for 900 mm => {ratio:.2f} mm/pt => Scale 1:{scale_S:.1f}")
