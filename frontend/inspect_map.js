// MapLibre Frontend Inspection Script
// Uses Playwright to actually drive the browser and run JS in the live app

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const errors = [];
  const maplibreErrors = [];
  const networkErrors = [];
  const consoleMessages = [];

  // Collect ALL console output
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error') errors.push(text);
    if (text.toLowerCase().includes('maplibre') || text.toLowerCase().includes('style') || text.toLowerCase().includes('source') || text.toLowerCase().includes('layer')) {
      maplibreErrors.push({ type: msg.type(), text });
    }
  });

  page.on('pageerror', err => errors.push('PAGE ERROR: ' + err.message));
  page.on('requestfailed', req => networkErrors.push(req.url() + ' — ' + req.failure().errorText));

  console.log('=== Navigating to http://localhost:5173 ===');
  await page.goto('http://localhost:5173', { waitUntil: 'domcontentloaded', timeout: 15000 });

  // Wait for React to mount
  await page.waitForTimeout(3000);

  console.log('\n=== PAGE TITLE ===');
  console.log(await page.title());

  // Wait longer for map + data to load
  console.log('\n=== Waiting for map and data to load (8s)... ===');
  await page.waitForTimeout(8000);

  // ── INSPECTION 1: Map object existence ──
  const mapExists = await page.evaluate(() => {
    // MapLibre stores the map instance on the canvas container
    const canvas = document.querySelector('.maplibregl-canvas');
    return !!canvas;
  });
  console.log('\n=== Q1: MapLibre canvas present ===');
  console.log(mapExists ? 'YES' : 'NO');

  // ── INSPECTION 2 & 3: Sources and Layers ──
  console.log('\n=== Q2/Q3: Map sources and layers ===');
  const styleInfo = await page.evaluate(() => {
    // Try to get the map from the React fiber or global
    const mapCanvas = document.querySelector('.maplibregl-canvas');
    if (!mapCanvas) return { error: 'No canvas found' };

    // MapLibre GL JS exposes map on canvas._map or via the container
    const container = mapCanvas.closest('.maplibregl-map');
    if (!container) return { error: 'No map container found' };

    // Access map instance via the internal property
    const mapKey = Object.keys(container).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternals'));

    // Try direct access via window (sometimes exposed)
    if (window.__mapInstance) {
      const map = window.__mapInstance;
      const style = map.getStyle();
      return {
        sources: Object.keys(style.sources),
        layers: style.layers.map(l => ({ id: l.id, type: l.type })),
        hasGridSource: !!style.sources['grid'],
        hasGridFillLayer: style.layers.some(l => l.id === 'grid-fill'),
        hasGridLineLayer: style.layers.some(l => l.id === 'grid-line'),
      };
    }

    return { error: 'Map not exposed on window.__mapInstance' };
  });
  console.log(JSON.stringify(styleInfo, null, 2));

  // ── Inject map exposure into window ──
  // We need to patch the running app to expose the map
  // The map is created inside React component — we need to find it via DOM
  const injected = await page.evaluate(() => {
    // Intercept maplibre-gl Map constructor to capture the instance
    // Check if maplibregl is available globally
    return typeof maplibregl !== 'undefined' ? 'global' : 'not-global';
  });
  console.log('\n=== MapLibre GL global availability ===');
  console.log(injected);

  // Try accessing map via the container element internal
  const mapInternals = await page.evaluate(() => {
    const container = document.querySelector('.maplibregl-map');
    if (!container) return { error: 'no container' };

    // MapLibre stores map in container._maplibre_map (internal)
    // Try the known internal property name
    const keys = Object.getOwnPropertyNames(container);
    const mapKey = keys.find(k => k.includes('map') || k.includes('Map'));
    
    // Try common internal storage patterns
    const possibleKeys = ['_map', '__map', 'map', '_maplibreMap'];
    for (const k of possibleKeys) {
      if (container[k] && typeof container[k].getStyle === 'function') {
        const style = container[k].getStyle();
        const sourceKeys = Object.keys(style.sources);
        const layerIds = style.layers.map(l => l.id);
        
        // Get grid source data
        let gridFeatureCount = 'unknown';
        let gridFillPaint = null;
        let gridFillVisibility = null;
        try {
          const src = container[k].getSource('grid');
          if (src) {
            const data = src._data;
            gridFeatureCount = data?.features?.length ?? 'source exists but no _data';
          }
          if (container[k].getLayer('grid-fill')) {
            gridFillPaint = container[k].getPaintProperty('grid-fill', 'fill-opacity');
            gridFillVisibility = container[k].getLayoutProperty('grid-fill', 'visibility');
          }
        } catch(e) {}
        
        return {
          foundVia: k,
          sources: sourceKeys,
          layers: layerIds,
          hasGrid: sourceKeys.includes('grid'),
          hasGridFill: layerIds.includes('grid-fill'),
          hasGridLine: layerIds.includes('grid-line'),
          gridFeatureCount,
          gridFillPaint,
          gridFillVisibility,
        };
      }
    }
    
    return { 
      error: 'Could not find map on container',
      containerKeys: Object.getOwnPropertyNames(container).slice(0, 20)
    };
  });
  console.log('\n=== Map internals via container ===');
  console.log(JSON.stringify(mapInternals, null, 2));

  // ── Try alternative: use React DevTools fiber to find map ref ──
  const reactInternals = await page.evaluate(() => {
    // Find the maplibregl-map container
    const el = document.querySelector('.maplibregl-map');
    if (!el) return { error: 'no map container' };
    
    // Walk React fiber tree to find the map ref
    const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternals') || k.startsWith('__reactContainer'));
    if (!fiberKey) return { error: 'no react fiber key' };
    
    let fiber = el[fiberKey];
    let map = null;
    let depth = 0;
    
    // Walk up/through fiber to find a ref with getStyle
    const walkFiber = (f, maxDepth = 30) => {
      if (!f || depth > maxDepth) return null;
      depth++;
      
      // Check if this fiber has a ref with map methods
      if (f.ref && typeof f.ref.getStyle === 'function') return f.ref;
      if (f.stateNode && typeof f.stateNode.getStyle === 'function') return f.stateNode;
      
      // Check memoizedState for refs
      let state = f.memoizedState;
      while (state) {
        if (state.memoizedState && typeof state.memoizedState.getStyle === 'function') return state.memoizedState;
        state = state.next;
      }
      
      return walkFiber(f.child, maxDepth) || walkFiber(f.sibling, maxDepth);
    };
    
    map = walkFiber(fiber);
    if (!map) {
      // Try parent
      let parent = fiber;
      for (let i = 0; i < 50 && parent; i++) {
        if (parent.memoizedState) {
          let s = parent.memoizedState;
          while (s) {
            if (s.memoizedState && s.memoizedState !== null && typeof s.memoizedState === 'object' && typeof s.memoizedState.getStyle === 'function') {
              map = s.memoizedState;
              break;
            }
            s = s.next;
          }
        }
        if (map) break;
        parent = parent.return;
      }
    }
    
    if (!map) return { error: 'Could not find map via fiber walk' };
    
    // Expose it globally for further tests
    window.__inspectedMap = map;
    
    const style = map.getStyle();
    const sourceKeys = Object.keys(style.sources || {});
    const layerIds = (style.layers || []).map(l => l.id);
    
    // Get detailed grid info
    let gridInfo = { error: 'no grid source' };
    try {
      const src = map.getSource('grid');
      if (src) {
        gridInfo = {
          type: src.type,
          hasData: !!(src._data),
          featureCount: src._data?.features?.length ?? 0,
        };
      }
    } catch(e) {
      gridInfo = { error: e.message };
    }
    
    let gridFillInfo = { exists: false };
    try {
      const layer = map.getLayer('grid-fill');
      if (layer) {
        gridFillInfo = {
          exists: true,
          fillOpacity: map.getPaintProperty('grid-fill', 'fill-opacity'),
          fillColor: map.getPaintProperty('grid-fill', 'fill-color'),
          visibility: map.getLayoutProperty('grid-fill', 'visibility'),
        };
      }
    } catch(e) {
      gridFillInfo = { exists: false, error: e.message };
    }
    
    return {
      mapFound: true,
      sources: sourceKeys,
      layerCount: layerIds.length,
      layers: layerIds,
      hasGrid: sourceKeys.includes('grid'),
      hasGridFill: layerIds.includes('grid-fill'),
      hasGridLine: layerIds.includes('grid-line'),
      gridSource: gridInfo,
      gridFillLayer: gridFillInfo,
      isLoaded: map.loaded(),
      isStyleLoaded: map.isStyleLoaded(),
      zoom: map.getZoom(),
      center: map.getCenter(),
    };
  });
  console.log('\n=== Map via React fiber ===');
  console.log(JSON.stringify(reactInternals, null, 2));

  // ── Check if map exposed from last eval ──
  const mapExposed = await page.evaluate(() => !!window.__inspectedMap);
  
  if (mapExposed) {
    // Q4: Simulate layer click and check setPaintProperty
    console.log('\n=== Q4/Q5: Simulating layer button click ===');
    
    // Click the NDVI layer in sidebar
    const layerButtons = await page.$$('.layer-item');
    console.log(`Found ${layerButtons.length} layer buttons`);
    
    if (layerButtons.length > 2) {
      // Click NDVI (index 2)
      await layerButtons[2].click();
      await page.waitForTimeout(500);
      
      const afterClick = await page.evaluate(() => {
        const map = window.__inspectedMap;
        if (!map) return { error: 'no map' };
        try {
          return {
            fillColor: map.getPaintProperty('grid-fill', 'fill-color'),
            fillOpacity: map.getPaintProperty('grid-fill', 'fill-opacity'),
            gridFeatureCount: map.getSource('grid')?._data?.features?.length ?? 0,
          };
        } catch(e) {
          return { error: e.message };
        }
      });
      console.log('After NDVI click:', JSON.stringify(afterClick, null, 2));
    }
    
    // Q7: Check actual feature colors in GeoJSON
    console.log('\n=== Q7/Q8: Feature colors in source ===');
    const featureColors = await page.evaluate(() => {
      const map = window.__inspectedMap;
      if (!map) return { error: 'no map' };
      const src = map.getSource('grid');
      if (!src || !src._data) return { error: 'no grid source data' };
      const features = src._data.features;
      return {
        count: features.length,
        sampleColors: features.slice(0, 5).map(f => f.properties.color),
        sampleValues: features.slice(0, 5).map(f => f.properties.value),
        hasColors: features.every(f => !!f.properties.color),
        colorsSample: [...new Set(features.slice(0, 20).map(f => f.properties.color))],
      };
    });
    console.log(JSON.stringify(featureColors, null, 2));
    
    // Q9: Opacity
    const opacityCheck = await page.evaluate(() => {
      const map = window.__inspectedMap;
      if (!map || !map.getLayer('grid-fill')) return { error: 'no fill layer' };
      return { opacity: map.getPaintProperty('grid-fill', 'fill-opacity') };
    });
    console.log('\n=== Q9: Opacity ===');
    console.log(JSON.stringify(opacityCheck));
    
    // Q10: Check for covering layers
    console.log('\n=== Q10: Layer order (what is above grid-fill?) ===');
    const layerOrder = await page.evaluate(() => {
      const map = window.__inspectedMap;
      if (!map) return { error: 'no map' };
      const style = map.getStyle();
      const layers = style.layers.map(l => l.id);
      const gridIdx = layers.indexOf('grid-fill');
      return {
        gridFillIndex: gridIdx,
        totalLayers: layers.length,
        layersBefore: layers.slice(Math.max(0, gridIdx - 3), gridIdx),
        layersAfter: layers.slice(gridIdx + 1, gridIdx + 10),
        allLayers: layers,
      };
    });
    console.log(JSON.stringify(layerOrder, null, 2));
    
    // Q12: map.loaded() / map.isStyleLoaded()
    const loadState = await page.evaluate(() => {
      const map = window.__inspectedMap;
      if (!map) return {};
      return { loaded: map.loaded(), styleLoaded: map.isStyleLoaded() };
    });
    console.log('\n=== Q12: Load state ===');
    console.log(JSON.stringify(loadState));
  }

  // ── Console errors summary ──
  console.log('\n=== CONSOLE ERRORS ===');
  if (errors.length === 0) {
    console.log('NONE');
  } else {
    errors.forEach(e => console.log('ERROR:', e));
  }
  
  console.log('\n=== MAP/STYLE RELATED CONSOLE MESSAGES ===');
  maplibreErrors.slice(0, 20).forEach(m => console.log(`[${m.type}]`, m.text));
  
  console.log('\n=== NETWORK FAILURES ===');
  if (networkErrors.length === 0) {
    console.log('NONE');
  } else {
    networkErrors.forEach(e => console.log('FAIL:', e));
  }
  
  console.log('\n=== ALL CONSOLE MESSAGES (last 30) ===');
  consoleMessages.slice(-30).forEach(m => console.log(`[${m.type}]`, m.text));

  await browser.close();
})();
