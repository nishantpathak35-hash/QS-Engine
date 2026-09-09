import urllib.request, json
from pathlib import Path

BASE = 'http://127.0.0.1:8000'
PDF  = Path('C:/Users/Admin/Downloads/DENTON LINK LEGAL FINAL 01-FURNITURE LAYOUT.pdf')

boundary = 'AuditBnd999'
with open(PDF, 'rb') as f:
    file_bytes = f.read()

body = (
    '--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + PDF.name + '"\r\nContent-Type: application/pdf\r\n\r\n'
).encode() + file_bytes + (
    '\r\n--' + boundary + '\r\nContent-Disposition: form-data; name="drawing_number"\r\n\r\nAUDIT-01\r\n--' + boundary + '--\r\n'
).encode()

req = urllib.request.Request(BASE + '/v1/drawings/upload', data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
with urllib.request.urlopen(req) as r:
    did = json.loads(r.read())['drawing_id']
print('Drawing ID: ' + did)

req2 = urllib.request.Request(BASE + '/v1/drawings/' + did + '/process',
    data=json.dumps({'assumed_units':'mm'}).encode(),
    headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req2) as r:
    resp = json.loads(r.read())

items  = resp.get('items', [])
totals = resp.get('totals', {})
bm     = resp.get('base_measurements', {})
est    = resp.get('priced_estimate', {})

print('\n=== BASE MEASUREMENTS ===')
for k,v in sorted(bm.items()):
    print('  ' + str(k) + ': ' + str(v))

print('\n=== ALL ' + str(len(items)) + ' LINE ITEMS (RAW) ===')
print('{:>3}  {:<12} {:>10} {:<8}  {:<18}  DESCRIPTION'.format('#','CODE','QTY','UNIT','STATUS'))
print('-'*95)
for i,it in enumerate(items, 1):
    code  = it['item_code']
    qty   = it['quantity']
    unit  = it['unit']
    status= it['status']
    desc  = it['description'][:60]
    flag  = ''
    if qty == 0:
        flag = ' <<ZERO QTY>>'
    elif unit in ('sqm','m2') and qty > 900:
        flag = ' <<HUGE AREA CHECK>>'
    elif unit == 'nos' and qty > 150:
        flag = ' <<HIGH COUNT CHECK>>'
    print('{:>3}. {:<12} {:>10.2f} {:<8}  {:<18}  {}{}'.format(i, code, qty, unit, status, desc, flag))

print('\n=== TOTALS ROLLUP ===')
print('{:<12} {:>10} {:>10} {:<8}  {:>7}  EXTRA       DESCRIPTION'.format('CODE','NET','GROSS','UNIT','WASTE%'))
print('-'*95)
for code, d in sorted(totals.items()):
    net   = d.get('net_quantity', 0)
    gross = d.get('gross_quantity', 0)
    unit  = d.get('unit', '?')
    w     = d.get('wastage_percent', 0) * 100
    desc  = d.get('description', '')[:40]
    extra = '[{:,.0f} sqft]'.format(net * 10.7639) if unit in ('sqm','m2') else ''
    flag  = ' <<ZERO>>' if net == 0 else ''
    print('{:<12} {:>10.2f} {:>10.2f} {:<8}  {:>7.1f}%  {:<14} {}{}'.format(
        code, net, gross, unit, w, extra, desc, flag))

print('\n=== PRICED ESTIMATE ===')
if est:
    print('  Direct Cost  INR {:>14,.2f}'.format(est.get('direct_cost_subtotal_inr',0)))
    print('  OH+P  10%    INR {:>14,.2f}'.format(est.get('contractor_overhead_profit_inr',0)))
    print('  Conting 3%   INR {:>14,.2f}'.format(est.get('contingency_inr',0)))
    print('  GST 18%      INR {:>14,.2f}'.format(est.get('gst_tax_inr',0)))
    print('  GRAND TOTAL  INR {:>14,.2f}'.format(est.get('grand_total_budget_inr',0)))
    print('  Rate/SQM     INR {:>14,.2f}'.format(est.get('cost_per_sqm_inr',0)))
    print('  Rate/SQFT    INR {:>14,.2f}'.format(est.get('cost_per_sqft_inr',0)))

    print('\n  TRADE BREAKDOWN:')
    for trade, amt in sorted(est.get('trade_subtotals_inr',{}).items(), key=lambda x:-x[1]):
        pct = (amt / max(est.get('direct_cost_subtotal_inr',1), 1)) * 100
        print('    {:<42} INR {:>12,.2f}  ({:.1f}%)'.format(trade, amt, pct))

    print('\n  PRICED ITEMS:')
    print('  {:<12} {:>10} {:>10} {:<8} {:>10}  {:>14}  {}'.format(
        'CODE','NET','GROSS','UNIT','RATE/u','TOTAL(INR)','DESC'))
    print('  '+'-'*90)
    for pi in est.get('items', []):
        code  = pi['item_code']
        nq    = pi['net_quantity']
        gq    = pi['gross_quantity']
        unit  = pi['unit']
        rate  = pi['unit_rate_inr']
        total = pi['total_amount_inr']
        desc  = pi['description'][:32]
        flag  = ''
        if rate < 500:
            flag = ' <<RATE LOW>>'
        elif rate > 200000:
            flag = ' <<RATE HIGH>>'
        if nq == 0:
            flag += ' <<ZERO QTY>>'
        if total < 1000 and nq > 0:
            flag += ' <<LOW TOTAL>>'
        print('  {:<12} {:>10.2f} {:>10.2f} {:<8} {:>10.0f}  {:>14,.0f}  {}{}'.format(
            code, nq, gq, unit, rate, total, desc, flag))
else:
    print('  <<NO ESTIMATE RETURNED>>')
