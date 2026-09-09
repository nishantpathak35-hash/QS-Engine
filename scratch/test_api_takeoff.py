import sys
from pathlib import Path
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

pdf_path = "C:/Users/Admin/Downloads/BRIDGE WAY-FURNITURE LAYOUT.pdf"
with open(pdf_path, "rb") as f:
    up_resp = client.post(
        "/v1/drawings/upload",
        files={"file": ("BRIDGE WAY-FURNITURE LAYOUT.pdf", f, "application/pdf")},
        data={"drawing_number": "BW-01", "revision": "01"}
    )

print("Upload Status:", up_resp.status_code)
data = up_resp.json()
drawing_id = data["drawing_id"]
print("Drawing ID:", drawing_id)

proc_resp = client.post(
    f"/v1/drawings/{drawing_id}/process",
    params={"scale_override": 100},
    json={
        "project_profile": {
            "scale_override": 100,
            "units": "mm"
        }
    }
)

print("Process Status:", proc_resp.status_code)
result = proc_resp.json()

print("\n=== AI INSIGHT ===")
ai = result.get("geometry", {}).get("ai_insight", {})
print("Discipline:", ai.get("discipline"), f"({ai.get('confidence', 0)*100:.1f}%)")
print("AI Provider:", ai.get("ai_provider_used"))
print("Reasons:", len(ai.get("reasons", [])))
for r in ai.get("reasons", []):
    print("  •", r)
print("\nSuppressed Trades:")
for st in ai.get("suppressed_trades", []):
    print("  [X]", st)

print("\n=== TOTALS / TAKEOFF ===")
totals = result.get("totals", {})
for code, val in totals.items():
    print(f"  {code:<8} | Net: {val.get('net_quantity'):>6} {val.get('unit'):<4} | Gross: {val.get('gross_quantity'):>6} | {val.get('description')}")

print("\n=== ARCHITECTURAL SPACES ===")
rooms = result.get("geometry", {}).get("rooms", [])
print(f"Total Spaces: {len(rooms)}")
for r in rooms:
    print(f"  {r['id']} | {r['name']:<35} | Area: {r['net_area_sqm']:>6.2f} sqm | Perimeter: {r['perimeter_m']:>5.2f} m")

print("\n=== PRICED ESTIMATE ===")
est = result.get("priced_estimate")
if est:
    print(f"Direct Cost: ₹{est['direct_cost_subtotal_inr']:,.2f}")
    print(f"Total Project Budget: ₹{est['net_project_cost_inr']:,.2f}")
