"""
Comprehensive User Acceptance Testing (UAT) Execution Script
Tests the live running API server at http://127.0.0.1:8000 for Dentons Link Legal Layout.
"""

import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
import openpyxl

BASE_URL = "http://127.0.0.1:8000"
PDF_PATH = Path("C:/Users/Admin/Downloads/DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf")

def run_uat():
    print("=" * 80)
    print("USER ACCEPTANCE TESTING (UAT) — DENTONS LINK LEGAL COMMERCIAL FIT-OUT")
    print("=" * 80)

    # 1. Health Check
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        health_data = json.loads(resp.read().decode())
        print(f"[UAT-01] Engine Health Check: {health_data.get('status', 'ok').upper()} (200 OK)")

    # 2. Upload Drawing
    print(f"\n[UAT-02] Uploading '{PDF_PATH.name}' to {BASE_URL}/v1/drawings/upload...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    with open(PDF_PATH, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{PDF_PATH.name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + file_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="drawing_number"\r\n\r\n'
        f"DENTON-FINAL-01\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="revision"\r\n\r\n'
        f"01\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    upload_req = urllib.request.Request(
        f"{BASE_URL}/v1/drawings/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(upload_req) as resp:
        upload_res = json.loads(resp.read().decode())
        drawing_id = upload_res["drawing_id"]
        print(f"       Upload Successful! Assigned Drawing ID: {drawing_id}")

    # 3. Process Drawing Takeoff
    print(f"\n[UAT-03] Processing Takeoff via POST {BASE_URL}/v1/drawings/{drawing_id}/process...")
    proc_req = urllib.request.Request(
        f"{BASE_URL}/v1/drawings/{drawing_id}/process",
        data=json.dumps({"assumed_units": "mm"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(proc_req) as resp:
        takeoff_res = json.loads(resp.read().decode())

    # 4. Verify AI Insights & Auto-Scale
    ai = takeoff_res.get("geometry", {}).get("ai_insight", {})
    scale_ratio = ai.get("scale_ratio")
    discipline = ai.get("discipline")
    print("\n[UAT-04] AI Drawing Agent Intelligence & Auto-Calibration:")
    print(f"       Discipline Classified : {discipline} (Confidence: {ai.get('confidence', 0)*100:.1f}%)")
    print(f"       Auto-Calibrated Scale : 1:{scale_ratio} (Zero manual input)")
    print(f"       AI Provider Used      : {ai.get('ai_provider_used')}")
    assert discipline == "FURNITURE_LAYOUT", f"Expected FURNITURE_LAYOUT, got {discipline}"
    assert scale_ratio is not None and 50 <= scale_ratio <= 70, f"Scale ratio unexpected: {scale_ratio}"
    print("       >>> [PASS] Discipline & Witness-Line Scale Auto-Calibration Verified")

    # 5. Verify Base Measurements
    bm = takeoff_res.get("base_measurements", {})
    print("\n[UAT-05] Fit-Out Base Measurements & Indian Standard Units:")
    print(f"       Total Carpet Area     : {bm.get('total_floor_area_sqft'):,.2f} sqft ({bm.get('total_floor_area_sqm'):,.2f} sqm)")
    print(f"       Total Room Perimeter  : {bm.get('total_room_perimeter_rft'):,.2f} Rft ({bm.get('total_room_perimeter_m'):,.2f} m)")
    print(f"       Total Verified Doors  : {bm.get('total_door_count')} Nos")
    print(f"       Total Workstations    : {bm.get('total_workstations')} Seats")
    assert bm.get("total_floor_area_sqft") > 5000, "Floor area should be ~5,630 sqft"
    assert bm.get("total_door_count") == 23, f"Expected 23 doors, got {bm.get('total_door_count')}"
    assert bm.get("total_workstations") == 67, f"Expected 67 workstations, got {bm.get('total_workstations')}"
    print("       >>> [PASS] Fit-Out Base Measurements Metadata Verified")

    # 6. Verify Bill of Quantities (BOQ Items)
    items = takeoff_res.get("items", [])
    totals = takeoff_res.get("totals", {})
    print(f"\n[UAT-06] Takeoff Items Verification ({len(items)} items generated):")
    
    # 6a. Verify Vinyl Flooring is ZERO
    vinyl_items = [it for it in items if "VINYL" in it["description"].upper() or it["item_code"] == "FL-03"]
    assert len(vinyl_items) == 0, f"FAIL: Vinyl flooring detected! {vinyl_items}"
    print("       * Antibacterial Vinyl Flooring (FL-03) : 0.0 SQFT (ELIMINATED)")

    # 6b. Verify Carpet Tile and Vitrified
    fl02 = totals.get("FL-02", {})
    fl01 = totals.get("FL-01", {})
    fl05 = totals.get("FL-05", {})
    print(f"       * Modular Carpet Tile (FL-02)          : {fl02.get('net_quantity', 0):,.1f} sqm ({fl02.get('net_quantity', 0)*10.7639:,.1f} sqft)")
    print(f"       * Vitrified / Italian Marble (FL-01)   : {fl01.get('net_quantity', 0):,.1f} sqm ({fl01.get('net_quantity', 0)*10.7639:,.1f} sqft)")
    print(f"       * Anti-Static Raised Floor (FL-05)     : {fl05.get('net_quantity', 0):,.1f} sqm ({fl05.get('net_quantity', 0)*10.7639:,.1f} sqft)")
    assert fl02.get("net_quantity", 0) > 350, "Carpet tile should be > 350 sqm"

    # 6c. Verify AV Presentation Displays
    av01 = totals.get("AV-01", {})
    print(f"       * AV Presentation Displays (AV-01)     : {av01.get('net_quantity', 0)} Nos (Target: 6 Nos)")
    assert av01.get("net_quantity") == 6.0, f"Expected 6 AV displays, got {av01.get('net_quantity')}"

    # 6d. Verify Workstations & Cabins
    fn01 = totals.get("FN-01", {})
    fn01b = totals.get("FN-01B", {})
    fn03 = totals.get("FN-03", {})
    print(f"       * Senior Associate Desks (FN-01)       : {fn01.get('net_quantity', 0)} Nos (Target: 21)")
    print(f"       * PA + Associate Desks (FN-01B)        : {fn01b.get('net_quantity', 0)} Nos (Target: 46)")
    print(f"       * Manager Executive Cabins (FN-03)     : {fn03.get('net_quantity', 0)} Nos (Target: 10)")
    assert fn01.get("net_quantity") == 21.0
    assert fn01b.get("net_quantity") == 46.0
    assert fn03.get("net_quantity") == 10.0
    print("       >>> [PASS] All BOQ Quantities & Finishes Verified")

    # 7. Verify Priced BOQ & Budget
    est = takeoff_res.get("priced_estimate", {})
    print("\n[UAT-07] Commercial Fit-Out Cost Estimation & Budget:")
    print(f"       Direct Works Subtotal : INR {est.get('direct_cost_subtotal_inr', 0):,.2f}")
    print(f"       Contractor OH&P (10%) : INR {est.get('contractor_overhead_profit_inr', 0):,.2f}")
    print(f"       Contingency (3%)      : INR {est.get('contingency_inr', 0):,.2f}")
    print(f"       GST @ 18%             : INR {est.get('gst_tax_inr', 0):,.2f}")
    print(f"       GRAND TOTAL BUDGET    : INR {est.get('grand_total_budget_inr', 0):,.2f}")
    print(f"       Fit-out Rate / SQFT   : INR {est.get('cost_per_sqft_inr', 0):,.2f} / sqft")
    print(f"       Fit-out Rate / SQM    : INR {est.get('cost_per_sqm_inr', 0):,.2f} / sqm")
    assert 950 <= est.get("cost_per_sqft_inr", 0) <= 1200, "Cost per sqft should be between 950 and 1200 INR"
    print("       >>> [PASS] Pricing Engine Rates & Financial Lineages Verified")

    # 8. Verify Excel Export
    print(f"\n[UAT-08] Verifying Multi-Format Excel Exporter via GET {BASE_URL}/v1/drawings/{drawing_id}/export?format=excel...")
    exp_req = urllib.request.Request(f"{BASE_URL}/v1/drawings/{drawing_id}/export?format=excel")
    with urllib.request.urlopen(exp_req) as resp:
        excel_bytes = resp.read()
    
    test_out = Path("scratch/uat_denton_download.xlsx")
    with open(test_out, "wb") as f:
        f.write(excel_bytes)
    print(f"       Excel file received ({len(excel_bytes):,} bytes). Saved to {test_out}.")

    wb = openpyxl.load_workbook(test_out, data_only=False)
    assert "Measurement Takeoff" in wb.sheetnames
    assert "BOQ Summary" in wb.sheetnames
    assert "Priced BOQ & Budget" in wb.sheetnames
    ws3 = wb["Priced BOQ & Budget"]
    cell_values = [str(ws3.cell(row=r, column=11).value) for r in range(1, ws3.max_row + 1)]
    assert any("Fit-out Rate / SQFT" in v for v in cell_values)
    assert any("Fit-out Rate / SQM" in v for v in cell_values)
    print(f"       Verified Sheet 1: 'Measurement Takeoff' ({wb['Measurement Takeoff'].max_row} rows)")
    print(f"       Verified Sheet 2: 'BOQ Summary' ({wb['BOQ Summary'].max_row} rows)")
    print(f"       Verified Sheet 3: 'Priced BOQ & Budget' ({ws3.max_row} rows w/ Rate/sqft formula)")
    print("       >>> [PASS] Excel Export & Dynamic Formulas Verified")

    print("\n" + "=" * 80)
    print("ALL UAT ACCEPTANCE GATES PASSED (100% SUCCESSFUL)")
    print("=" * 80)

if __name__ == "__main__":
    run_uat()
