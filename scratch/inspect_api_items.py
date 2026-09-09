import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8000/v1/drawings/DRW-28A0A741/quantities')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
print('Takeoff item count:', len(data['items']))
for it in data['items']:
    print(f"  {it['item_code']}: {it['quantity']} ({it['description'][:50]})")
