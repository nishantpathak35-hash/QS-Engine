from vision.ai_drawing_agent import AIDrawingAgent
from qs.rule_engine import QSRuleEngine
from pricing.cost_engine import CostEstimationEngine, FitoutGrade
from exports.exporter import QSExporter

path = 'C:/Users/Admin/Downloads/DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf'
insight = AIDrawingAgent.analyze_pdf(path)
print('=== AI INSIGHT ===')
print('Discipline:', insight.discipline)
print('Scale Ratio:', insight.scale_ratio)
print('Scale mm/pt:', insight.scale_mm_per_pt)
print('Entities count:', len(insight.detected_entities))
for k, v in insight.detected_entities.items():
    print(f"  {k}: {v['quantity']} {v['unit']} - {v['description']}")

total_sqm = sum(s['area_sqm'] for s in insight.spaces)
print(f"\nTotal Spaces: {len(insight.spaces)}, Total Area: {total_sqm:.2f} m2 ({total_sqm*10.7639104:.1f} sqft)")

rooms = AIDrawingAgent.generate_semantic_rooms(insight, 'DWG-DENTON', insight.scale_mm_per_pt)
ai_items = AIDrawingAgent.generate_takeoff_items(insight, 'DWG-DENTON', 'DENTON-01')

rule_engine = QSRuleEngine()
takeoff = rule_engine.calculate_takeoff('DWG-DENTON', 'DENTON-01', '0', rooms, [], [])
takeoff.items = [it for it in takeoff.items if it.item_code not in ('FL-RAW', 'CL-RAW', 'PT-RAW', 'PT-01')]
takeoff.items.extend(ai_items)

print('\n=== TAKEOFF BASE MEASUREMENTS ===')
print(takeoff.base_measurements)

print('\n=== PRICED ESTIMATE ===')
est = CostEstimationEngine.estimate_project_cost(takeoff, FitoutGrade.STANDARD)
print(f"Direct Cost: INR {est.direct_cost_subtotal_inr:,.2f}")
print(f"Grand Total: INR {est.grand_total_budget_inr:,.2f}")
print(f"Cost per sqm: INR {est.cost_per_sqm_inr:,.2f}/m2")
print(f"Cost per sqft: INR {est.cost_per_sqft_inr:,.2f}/sqft")

print('\nTrade subtotals:')
for trade, amt in est.trade_subtotals_inr.items():
    print(f"  {trade}: INR {amt:,.2f}")
