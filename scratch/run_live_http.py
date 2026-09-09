import urllib.request
import json
from pathlib import Path

# Use requests or httpx if available
import httpx

pdf_path = Path("C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf")
with open(pdf_path, "rb") as f:
    files = {"file": ("BRIDGE WAY-FURNITURE LAYOUT.pdf", f, "application/pdf")}
    data = {"drawing_number": "BW-01", "revision": "01"}
    r = httpx.post("http://127.0.0.1:8000/v1/drawings/upload", files=files, data=data)

upload_json = r.json()
drawing_id = upload_json["drawing_id"]
print("Live Upload OK:", drawing_id)

p = httpx.post(f"http://127.0.0.1:8000/v1/drawings/{drawing_id}/process", timeout=30.0)
print("Live Process Status:", p.status_code)
res = p.json()
ai = res["geometry"]["ai_insight"]
print("Discipline:", ai["discipline"])
print("Auto-Calibrated Scale Ratio:", ai["scale_ratio"])
print("Workstations:", res["totals"].get("FN-01", {}).get("net_quantity"))
print("Fake Drywall in Totals:", "PT-01" in res["totals"])
