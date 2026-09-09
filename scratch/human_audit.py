"""
CTO Human Audit Script - Fresh Eyes
Upload → Process → Print EVERY line item with quantity, unit, description
Check for: Missing items, wrong units, wrong quantities, suspicious descriptions
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import urllib.request
import urllib.parse
import json
import sys
from pathlib import Path

BASE = "http://127.0.0.1:8000"
PDF  = Path("C:/Users/Admin/Downloads/DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf")

print("=" * 90)
print("CTO HUMAN AUDIT — RAW INSPECTION OF EVERY API ITEM")
print("=" * 90)

# Step 1: Upload
boundary = "----AuditBoundary7MA4"
with open(PDF, "rb") as f:
    file_bytes = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{PDF.name}"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + file_bytes + (
    f"\r\n--{boundary}\r\n"
    f'Content-Disposition: form-data; name="drawing_number"\r\nContent-Type: text/plain\r\n\r\nDENTON-AUDIT\r\n'
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="revision"\r\nContent-Type: text/plain\r\n\r\n01\r\n'
    f"--{boundary}--\r\n"
).encode()

req = urllib.request.Request(
    f"{BASE}/v1/drawings/upload", data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST"
)
with urllib.request.urlopen(req) as r:
    did = json.loads(r.read())["drawing_id"]
print(f"\nDrawing ID: {did}")

# Step 2: Process
req2 = urllib.request.Request(
    f"{BASE}/v1/drawings/{did}/process",
    data=json.dumps({"assumed_units": "mm"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST"
)
with urllib.request.urlopen(req2) as r:
    resp = json.loads(r.read())

items  = resp.get("items", [])
totals = resp.get("totals", {})
bm     = resp.get("base_measurements", {})
est    = resp.get("priced_estimate", {})

# ─── BASE MEASUREMENTS ───────────────────────────────────────────────────────
print("\n" + "─" * 90)
print("BASE MEASUREMENTS")
print("─" * 90)
for k, v in sorted(bm.items()):
    print(f"  {k:42s}: {v}")

# ─── EVERY LINE ITEM — RAW ───────────────────────────────────────────────────
print("\n" + "─" * 90)
print(f"ALL LINE ITEMS ({len(items)} total) — RAW DUMP")
print("─" * 90)
print(f"{'#':>3}  {'CODE':<12} {'QTY':>10} {'UNIT':<8}  {'STATUS':<16}  DESCRIPTION")
print("-" * 90)

for i, it in enumerate(items, 1):
    code   = it["item_code"]
    qty    = it["quantity"]
    unit   = it["unit"]
    status = it["status"]
    desc   = it["description"][:65]
    flag   = ""
    # Suspicious checks
    if qty == 0:
        flag = "  ⚠️  ZERO QTY!"
    elif unit in ("sqm", "m2") and qty > 1000:
        flag = "  ⚠️  HUGE AREA?"
    elif unit == "nos" and qty > 200:
        flag = "  ⚠️  COUNT > 200?"
    print(f"{i:>3}. {code:<12} {qty:>10.2f} {unit:<8}  {status:<16}  {desc}{flag}")

# ─── TOTALS ROLLUP ───────────────────────────────────────────────────────────
print("\n" + "─" * 90)
print("AGGREGATED TOTALS BY CODE")
print("─" * 90)
print(f"{'CODE':<12} {'NET QTY':>12} {'GROSS PO':>12} {'UNIT':<8}  {'WASTAGE':>8}  DESCRIPTION")
print("-" * 90)
for code, d in sorted(totals.items()):
    net   = d.get("net_quantity", 0)
    gross = d.get("gross_quantity", 0)
    unit  = d.get("unit", "?")
    w     = d.get("wastage_percent", 0) * 100
    desc  = d.get("description", "")[:50]
    flag  = ""
    if net == 0:
        flag = "  ⚠️  ZERO!"
    # Sqm → sqft conversion to verify sanity
    if unit in ("sqm", "m2"):
        sqft = net * 10.7639104
        flag += f"  [{sqft:,.0f} sqft]"
    print(f"{code:<12} {net:>12.2f} {gross:>12.2f} {unit:<8}  {w:>7.1f}%  {desc}{flag}")

# ─── PRICING SANITY ──────────────────────────────────────────────────────────
print("\n" + "─" * 90)
print("PRICED ESTIMATE SANITY CHECK")
print("─" * 90)
if est:
    print(f"  Fitout Grade        : {est.get('fitout_grade')}")
    print(f"  Direct Cost (₹)     : {est.get('direct_cost_subtotal_inr'):>18,.2f}")
    print(f"  OH & Profit 10% (₹) : {est.get('contractor_overhead_profit_inr'):>18,.2f}")
    print(f"  Contingency 3% (₹)  : {est.get('contingency_inr'):>18,.2f}")
    print(f"  GST 18% (₹)         : {est.get('gst_tax_inr'):>18,.2f}")
    print(f"  GRAND TOTAL (₹)     : {est.get('grand_total_budget_inr'):>18,.2f}")
    print(f"  Cost / SQM  (₹)     : {est.get('cost_per_sqm_inr'):>18,.2f}")
    print(f"  Cost / SQFT (₹)     : {est.get('cost_per_sqft_inr'):>18,.2f}")

    # Trade subtotals
    trade_sub = est.get("trade_subtotals_inr", {})
    if trade_sub:
        print(f"\n  TRADE PACKAGE BREAKDOWN:")
        for trade, amt in sorted(trade_sub.items(), key=lambda x: -x[1]):
            pct = (amt / est.get("direct_cost_subtotal_inr", 1)) * 100
            print(f"    {trade:<40} ₹{amt:>14,.2f}  ({pct:.1f}%)")

    # Per-item pricing
    print(f"\n  PRICED ITEMS:")
    print(f"  {'CODE':<12} {'NET QTY':>10} {'GROSS PO':>10} {'UNIT':<8} {'RATE/u':>10}  {'TOTAL':>14}  DESCRIPTION")
    print("  " + "-" * 85)
    for pi in est.get("items", []):
        code  = pi["item_code"]
        nq    = pi["net_quantity"]
        gq    = pi["gross_quantity"]
        unit  = pi["unit"]
        rate  = pi["unit_rate_inr"]
        total = pi["total_amount_inr"]
        desc  = pi["description"][:40]
        # Rate sanity
        flag = ""
        if rate < 100:
            flag = "  ⚠️  RATE < ₹100?"
        elif rate > 500000:
            flag = "  ⚠️  RATE > ₹5L?"
        print(f"  {code:<12} {nq:>10.2f} {gq:>10.2f} {unit:<8} {rate:>10.2f}  ₹{total:>13,.2f}  {desc}{flag}")
else:
    print("  ⚠️  No priced estimate returned!")

print("\n" + "=" * 90)
print("AUDIT COMPLETE — REVIEW ALL ⚠️ FLAGS ABOVE")
print("=" * 90)
