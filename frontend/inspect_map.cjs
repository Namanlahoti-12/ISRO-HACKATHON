const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  const consoleLog = [];
  const networkFails = [];

  page.on('console', msg => {
    const t = `[${msg.type()}] ${msg.text()}`;
    consoleLog.push(t);
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('requestfailed', r => networkFails.push(r.url() + ' => ' + (r.failure() || {}).errorText));

  await page.goto('http://localhost:5173', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(12000); // wait for React + map + API data

  // ── Expose map via fiber walk ──
  const result = await page.evaluate(() => {
    const out = {};

    // Q1: canvas present?
    out.q1_canvas = !!document.querySelector('.maplibregl-canvas');
    out.q1_container = !!document.querySelector('.maplibregl-map');

    // Walk React fiber to find map ref
    const el = document.querySelector('.map-container');
    if (!el) { out.fiberError = 'no .map-container'; return out; }

    const fiberKey = Object.keys(el).find(k =>
      k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
    );
    if (!fiberKey) { out.fiberError = 'no react fiber on .map-container'; return out; }

    let map = null;

    const walk = (fiber, depth) => {
      if (!fiber || depth > 200 || map) return;
      // Check memoizedState chain for useRef values holding a map
      let s = fiber.memoizedState;
      while (s) {
        const v = s.memoizedState;
        if (v && typeof v === 'object' && typeof v.getStyle === 'function') {
          map = v; return;
        }
        // useRef stores in { current: ... }
        if (v && v.current && typeof v.current.getStyle === 'function') {
          map = v.current; return;
        }
        s = s.next;
      }
      walk(fiber.child, depth + 1);
      if (!map) walk(fiber.sibling, depth + 1);
    };

    walk(el[fiberKey], 0);

    if (!map) {
      // try parent fibers
      let f = el[fiberKey].return;
      for (let i = 0; i < 100 && f && !map; i++, f = f.return) {
        let s = f.memoizedState;
        while (s) {
          const v = s.memoizedState;
          if (v && typeof v === 'object' && typeof v.getStyle === 'function') { map = v; break; }
          if (v && v.current && typeof v.current.getStyle === 'function') { map = v.current; break; }
          s = s.next;
        }
      }
    }

    if (!map) { out.fiberError = 'map not found in fiber tree'; return out; }

    window.__map = map;
    out.mapFound = true;
    out.mapLoaded = map.loaded();
    out.mapStyleLoaded = map.isStyleLoaded();
    out.zoom = map.getZoom();

    // Q2/Q3: sources and layers
    const style = map.getStyle();
    out.q2_sources = Object.keys(style.sources || {});
    out.q3_layers = (style.layers || []).map(l => ({ id: l.id, type: l.type }));
    out.q3_hasGridFill = out.q3_layers.some(l => l.id === 'grid-fill');
    out.q3_hasGridLine = out.q3_layers.some(l => l.id === 'grid-line');
    out.q2_hasGridSource = out.q2_sources.includes('grid');

    // Q7: features in source
    try {
      const src = map.getSource('grid');
      if (src && src._data) {
        const feats = src._data.features;
        out.q7_featureCount = feats.length;
        out.q7_sampleColors = feats.slice(0, 5).map(f => f.properties?.color);
        out.q7_sampleValues = feats.slice(0, 5).map(f => f.properties?.value);
        out.q7_allHaveColor = feats.every(f => !!f.properties?.color);
        out.q7_colorNull = feats.filter(f => !f.properties?.color).length;
      } else {
        out.q7_featureCount = 'source missing or no _data';
      }
    } catch(e) { out.q7_error = e.message; }

    // Q8/Q9: paint properties
    try {
      if (map.getLayer('grid-fill')) {
        out.q8_fillColor = map.getPaintProperty('grid-fill', 'fill-color');
        out.q9_fillOpacity = map.getPaintProperty('grid-fill', 'fill-opacity');
        out.q5_visibility = map.getLayoutProperty('grid-fill', 'visibility');
      } else {
        out.q8_fillColor = 'layer not found';
      }
    } catch(e) { out.q8_error = e.message; }

    // Q10: layer order — what's above grid-fill?
    const allLayerIds = (style.layers || []).map(l => l.id);
    const gridIdx = allLayerIds.indexOf('grid-fill');
    out.q10_gridFillIndex = gridIdx;
    out.q10_totalLayers = allLayerIds.length;
    out.q10_layersAboveGrid = allLayerIds.slice(gridIdx + 1);

    // Q11: what layer was grid-fill inserted before?
    out.q11_firstLayerAboveGrid = allLayerIds[gridIdx + 1] || 'none (top)';

    return out;
  });

  console.log('=== INSPECTION RESULT ===');
  console.log(JSON.stringify(result, null, 2));

  // Q4/Q5: Click a layer button and check map state changes
  const layerItems = await page.$$('.layer-item');
  console.log('\n=== Layer buttons found:', layerItems.length, '===');

  if (layerItems.length > 2 && result.mapFound) {
    // click NDVI (index 2)
    await layerItems[2].click();
    await page.waitForTimeout(800);

    const afterClick = await page.evaluate(() => {
      const map = window.__map;
      if (!map) return { error: 'no map' };
      try {
        const src = map.getSource('grid');
        return {
          q4_fillColor: map.getPaintProperty('grid-fill', 'fill-color'),
          q5_opacity: map.getPaintProperty('grid-fill', 'fill-opacity'),
          q6_featureCount: src?._data?.features?.length ?? 0,
          q6_sampleColor: src?._data?.features?.[0]?.properties?.color ?? 'n/a',
        };
      } catch(e) { return { error: e.message }; }
    });
    console.log('\n=== After NDVI layer click ===');
    console.log(JSON.stringify(afterClick, null, 2));

    // click LST (index 1)
    await layerItems[1].click();
    await page.waitForTimeout(800);
    const afterLST = await page.evaluate(() => {
      const map = window.__map;
      if (!map) return { error: 'no map' };
      try {
        const src = map.getSource('grid');
        return {
          fillColor: map.getPaintProperty('grid-fill', 'fill-color'),
          sampleColor: src?._data?.features?.[0]?.properties?.color,
        };
      } catch(e) { return { error: e.message }; }
    });
    console.log('\n=== After LST layer click ===');
    console.log(JSON.stringify(afterLST, null, 2));
  }

  // Q13: All errors
  console.log('\n=== JS/MapLibre ERRORS ===');
  if (errors.length === 0) console.log('NONE');
  else errors.forEach(e => console.log('ERR:', e));

  console.log('\n=== NETWORK FAILURES ===');
  if (networkFails.length === 0) console.log('NONE');
  else networkFails.forEach(f => console.log('FAIL:', f));

  console.log('\n=== CONSOLE LOG (last 40) ===');
  consoleLog.slice(-40).forEach(l => console.log(l));

  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
