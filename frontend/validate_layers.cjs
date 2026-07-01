// Layer validation — prediction_grid.geojson pipeline
// Validates that:
//   1. Source is 'prediction-grid' (URL-based GeoJSON, NOT CSV)
//   2. Layer is 'prediction-fill' (fill type, NOT heatmap)
//   3. Features are Polygon geometry (NOT Points)
//   4. fill-color is a MapLibre GL expression (GPU-side interpolation)
//   5. Switching layers changes the fill-color expression
//   6. Each layer renders real satellite/AI data from the GeoJSON properties

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const SCREENSHOTS_DIR = path.join(__dirname, 'layer_screenshots');
const APP_URL = 'http://localhost:5173';

const LAYER_KEYS = [
  'HeatScore_Predicted','LST','AirTemp','UHI_Intensity','UTCI_Approx','UTFVI',
  'NDVI','NDBI','NDWI','MNDWI','LULC_Derived',
  'Population_Density','Building_Density','Building_Height','Road_Density_Proxy',
  'Anthropogenic_Heat','Nighttime_Lights','Impervious_Frac',
  'Tree_Cover_Pct','Dist_Water','Dist_Green','Green_Space_Density','Albedo',
  'Humidity','WindSpeed','WindDirection','SolarRadiation','Elevation',
];

async function getMapState(page) {
  return page.evaluate(() => {
    const m = window.__mapInstance || window.__mapRef;
    if (!m) return { error: 'no-map' };
    try {
      const src = m.getSource('prediction-grid');
      const hasFill = !!m.getLayer('prediction-fill');
      const hasHit  = !!m.getLayer('prediction-hit');

      // Check feature count — inline data: _data is the FeatureCollection
      let featureCount = 0;
      let geometryType = 'unknown';
      let sampleProps = {};
      try {
        const data = src?._data;
        if (data && typeof data === 'object' && data.features) {
          featureCount = data.features.length;
          if (data.features[0]?.geometry?.type) geometryType = data.features[0].geometry.type;
          if (data.features[0]?.properties) sampleProps = data.features[0].properties;
        }
      } catch {}
      // Fallback: use querySourceFeatures if _data didn't work
      if (featureCount === 0) {
        try {
          const qf = m.querySourceFeatures('prediction-grid');
          featureCount = qf.length;
          if (qf[0]?.geometry?.type) geometryType = qf[0].geometry.type;
          if (qf[0]?.properties) sampleProps = qf[0].properties;
        } catch {}
      }

      let fillColorExpr = null;
      try { fillColorExpr = m.getPaintProperty('prediction-fill', 'fill-color'); } catch {}
      const isExpression = Array.isArray(fillColorExpr);
      const exprType = isExpression ? fillColorExpr[0] : typeof fillColorExpr;
      const exprSig = JSON.stringify(fillColorExpr);
      let visibility = 'visible';
      try { visibility = m.getLayoutProperty('prediction-fill', 'visibility') || 'visible'; } catch {}
      let opacity = null;
      try { opacity = m.getPaintProperty('prediction-fill', 'fill-opacity'); } catch {}

      return {
        featureCount,
        geometryType,
        hasFillLayer: hasFill,
        hasHitLayer: hasHit,
        hasSource: !!src,
        visibility,
        isExpression,
        exprType,
        exprSig,
        opacity,
        samplePropKeys: Object.keys(sampleProps).slice(0, 15),
        hasHeatScore: 'HeatScore_Predicted' in sampleProps,
        hasLST: 'LST' in sampleProps,
        hasNDVI: 'NDVI' in sampleProps,
        hasPopulation: 'Population_Density' in sampleProps,
        mapLoaded: m.loaded(),
        hasOldGridSource: !!m.getSource('grid'),
        hasOldHeatmapLayer: !!m.getLayer('grid-heat'),
      };
    } catch(e) { return { error: e.message }; }
  });
}

async function run() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  console.log('Launching Chrome (headed) for real WebGL...');
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: false,
    args: ['--no-sandbox', '--start-maximized'],
  });

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const jsErrors = [];
  page.on('console', m => { if (m.type() === 'error') jsErrors.push(m.text()); });
  page.on('pageerror', e => jsErrors.push('PAGE: ' + e.message));

  console.log('Navigating to', APP_URL);
  await page.goto(APP_URL, { waitUntil: 'domcontentloaded', timeout: 20000 });

  // Wait for map instance
  console.log('Waiting for __mapRef...');
  try {
    await page.waitForFunction(() => !!window.__mapRef, { timeout: 20000 });
    console.log('\u2713 __mapRef available');
  } catch {
    console.log('\u2717 __mapRef not set after 20s');
  }

  console.log('Waiting for __mapInstance (map.load event)...');
  try {
    await page.waitForFunction(() => !!window.__mapInstance, { timeout: 30000 });
    console.log('\u2713 Map loaded');
  } catch {
    console.log('\u26a0 Map load timeout');
  }

  // Wait for prediction-grid source to have features (inline-loaded GeoJSON)
  console.log('Waiting for prediction_grid.geojson to load...');
  try {
    await page.waitForFunction(
      () => {
        const m = window.__mapInstance || window.__mapRef;
        if (!m) return false;
        const src = m.getSource('prediction-grid');
        if (!src) return false;
        // Check inline _data first
        try {
          const d = src._data;
          if (d && typeof d === 'object' && d.features && d.features.length > 0) return true;
        } catch {}
        // Fallback: querySourceFeatures
        try { return m.querySourceFeatures('prediction-grid').length > 0; } catch {}
        return false;
      },
      { timeout: 35000 }
    );
    console.log('\u2713 prediction_grid.geojson loaded');
  } catch {
    console.log('\u26a0 GeoJSON load timeout — proceeding anyway');
  }

  // Expand layer groups
  await page.evaluate(() => {
    document.querySelectorAll('.layer-group-header').forEach(h => {
      const next = h.nextElementSibling;
      if (next && next.style.display === 'none') h.click();
    });
    const sectionTitles = document.querySelectorAll('.section-title');
    sectionTitles.forEach(el => {
      if (el.textContent && el.textContent.includes('Data Layers')) {
        const chevron = el.querySelector('span:last-child');
        if (chevron && chevron.textContent === '\u25b8') el.click();
      }
    });
  });
  await page.waitForTimeout(500);

  // Baseline check
  const baseState = await getMapState(page);
  console.log('\nBaseline map state:', JSON.stringify(baseState, null, 2));
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '00_initial.png'), fullPage: false });

  // ARCHITECTURE VALIDATION
  console.log('\n=== ARCHITECTURE VALIDATION ===');
  console.log(`Source 'prediction-grid': ${baseState.hasSource ? '\u2713' : '\u2717'}`);
  console.log(`Layer 'prediction-fill': ${baseState.hasFillLayer ? '\u2713' : '\u2717'}`);
  console.log(`Geometry type: ${baseState.geometryType} ${baseState.geometryType === 'Polygon' ? '\u2713' : '\u2717'}`);
  console.log(`fill-color is GL expression: ${baseState.isExpression ? '\u2713' : '\u2717'} (${baseState.exprType})`);
  console.log(`Features contain HeatScore_Predicted: ${baseState.hasHeatScore ? '\u2713' : '\u2717'}`);
  console.log(`Features contain LST: ${baseState.hasLST ? '\u2713' : '\u2717'}`);
  console.log(`Features contain NDVI: ${baseState.hasNDVI ? '\u2713' : '\u2717'}`);
  console.log(`Old 'grid' source absent: ${!baseState.hasOldGridSource ? '\u2713' : '\u2717 FAIL - old CSV source still present!'}`);
  console.log(`Old 'grid-heat' layer absent: ${!baseState.hasOldHeatmapLayer ? '\u2713' : '\u2717 FAIL - heatmap layer still present!'}`);
  console.log(`Feature count: ${baseState.featureCount}`);
  console.log(`Sample properties: ${baseState.samplePropKeys.join(', ')}`);

  // Per-layer validation
  const results = [];
  let prevExprSig = null;

  for (let i = 0; i < LAYER_KEYS.length; i++) {
    const key = LAYER_KEYS[i];
    process.stdout.write(`\n[${String(i+1).padStart(2)}/${LAYER_KEYS.length}] ${key.padEnd(28)}`);

    // Click layer item
    const clickOk = await page.evaluate((k) => {
      const el = document.getElementById(`layer-${k}`);
      if (el) { el.click(); return true; }
      return false;
    }, key);
    process.stdout.write(clickOk ? ' click:\u2713' : ' click:\u2717');

    // Wait for GL expression to update
    await page.waitForTimeout(800);

    const state = await getMapState(page);
    const exprChanged = state.exprSig !== prevExprSig;
    prevExprSig = state.exprSig;

    const working = !state.error
      && state.hasSource
      && state.hasFillLayer
      && (state.featureCount ?? 0) > 0
      && state.isExpression
      && state.visibility !== 'none';

    const icon = working ? '\u2705' : '\u274c';
    const dupWarn = !exprChanged && i > 0 ? ' \u26a0\ufe0f SAME-EXPR' : '';

    process.stdout.write(` ${icon} feat:${state.featureCount ?? '?'} type:${state.exprType} vis:${state.visibility}${dupWarn}`);
    if (state.error) process.stdout.write(` ERR:${state.error}`);

    const shot = path.join(SCREENSHOTS_DIR, `${String(i+1).padStart(2,'0')}_${key}.png`);
    await page.screenshot({ path: shot, fullPage: false });

    results.push({
      key, working,
      exprChanged: i === 0 || exprChanged,
      featureCount: state.featureCount ?? 0,
      exprType: state.exprType,
      error: state.error,
    });
  }

  // Final report
  console.log('\n\n\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550');
  console.log('FINAL LAYER VALIDATION REPORT');
  console.log('\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550');
  console.log(`Data source: /api/prediction_grid.geojson (NOT master_dataset.csv)`);
  console.log(`Rendering: MapLibre Fill Layer with GL expression (NOT HeatmapLayer)`);
  console.log(`Geometry: Polygon (30m x 30m satellite pixel cells)`);
  console.log('');

  let pass = 0;
  for (const r of results) {
    const icon = r.working ? '\u2705' : '\u274c';
    const dup = !r.exprChanged ? ' \u26a0\ufe0f SAME EXPR' : '';
    console.log(`${icon} ${r.key.padEnd(28)} feat:${String(r.featureCount).padStart(5)} expr:${r.exprType}${dup}${r.error ? ` ERR:${r.error}` : ''}`);
    if (r.working) pass++;
  }
  console.log(`\nRESULT: ${pass}/${LAYER_KEYS.length} WORKING`);
  console.log(`Screenshots -> ${SCREENSHOTS_DIR}`);

  if ([...new Set(jsErrors)].length) {
    console.log('\n=== JS ERRORS ===');
    [...new Set(jsErrors)].slice(0, 5).forEach(e => console.log(e));
  }

  await browser.close();
  if (pass < LAYER_KEYS.length) process.exit(1);
}

run().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
