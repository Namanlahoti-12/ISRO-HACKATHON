import urllib.request, json

endpoints = {
    'config': 'http://localhost:5000/api/config',
    'health': 'http://localhost:5000/api/health',
    'grid': 'http://localhost:5000/api/grid',
    'pixel': 'http://localhost:5000/api/pixel/100',
}

for name, url in endpoints.items():
    try:
        r = urllib.request.urlopen(url, timeout=20)
        d = json.loads(r.read())
        if name == 'config':
            print(f"[OK] {name}: pixels={d['total_pixels']}, model={d['model_name']}")
        elif name == 'grid':
            print(f"[OK] {name}: {len(d['pixels'])} pixels, {len(d['columns'])} cols")
        elif name == 'pixel':
            print(f"[OK] {name}: score={d['heat_score']}, class={d['heat_class']}, drivers={len(d['top_drivers'])}")
        else:
            print(f"[OK] {name}: {d.get('status', 'ok')}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

# Test frontend
r2 = urllib.request.urlopen('http://localhost:5000/')
html = r2.read().decode()
has_root = 'id="root"' in html
has_assets = 'assets/' in html
has_title = 'Urban Heat AI' in html
print(f"[{'OK' if has_root else 'FAIL'}] React root div")
print(f"[{'OK' if has_assets else 'FAIL'}] Vite bundle ref")
print(f"[{'OK' if has_title else 'FAIL'}] Page title")
