/**
 * Urban Heat AI — Google Maps Dashboard
 * ======================================
 * Full-featured Google Maps integration with:
 *   - 14 toggleable data overlay layers
 *   - Per-pixel click detail with SHAP contributions
 *   - Interactive scenario simulator with live map updates
 *   - Google Places search (city, address, lat/lng, pincode, landmark)
 *   - Export (PNG, GeoJSON, CSV)
 *   - Optimized rendering for thousands of 30m grid cells
 */

const API = '/api';

// ═══════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════
let map = null;
let gridPixels = [];
let gridStats = {};
let gridRectangles = [];
let heatmapLayer = null;
let infoWindow = null;
let searchBox = null;
let selectedPixel = null;
let scenarioData = null;
let config = {};

let currentLayer = 'HeatScore_Predicted';
let gridOpacity = 0.7;
let simView = 'before'; // before | after | diff

// ═══════════════════════════════════════════════════════════════
//  LAYER DEFINITIONS (14 data layers + Heat Score)
// ═══════════════════════════════════════════════════════════════
const LAYERS = {
    HeatScore_Predicted: { name: 'Urban Heat Score', icon: '🌡️', unit: '0–100', colors: ['#2166ac','#67a9cf','#d1e5f0','#fddbc7','#ef8a62','#b2182b'] },
    LST:                 { name: 'Land Surface Temp', icon: '🔥', unit: '°C', colors: ['#313695','#4575b4','#abd9e9','#fee090','#f46d43','#a50026'] },
    NDVI:                { name: 'NDVI (Vegetation)', icon: '🌿', unit: '-1 to 1', colors: ['#8c510a','#d8b365','#f6e8c3','#c7eae5','#5ab4ac','#01665e'] },
    NDBI:                { name: 'NDBI (Built-up)', icon: '🏗️', unit: '-1 to 1', colors: ['#1a9850','#91cf60','#d9ef8b','#fee08b','#fc8d59','#d73027'] },
    NDWI:                { name: 'NDWI (Water)', icon: '💧', unit: '-1 to 1', colors: ['#d73027','#fc8d59','#fee08b','#d9ef8b','#91cf60','#1a9850'] },
    Population_Density:  { name: 'Population Density', icon: '👥', unit: 'ppl/px', colors: ['#f7f7f7','#d9d9d9','#bdbdbd','#969696','#636363','#252525'] },
    Building_Density:    { name: 'Building Density', icon: '🏢', unit: '%', colors: ['#f7f7f7','#cccccc','#969696','#636363','#252525','#000000'] },
    Road_Density_Proxy:  { name: 'Road Density', icon: '🛣️', unit: 'index', colors: ['#ffffd4','#fee391','#fec44f','#fe9929','#d95f0e','#993404'] },
    Nighttime_Lights:    { name: 'Night-time Lights', icon: '🌃', unit: 'nW', colors: ['#0d0d0d','#1a1a2e','#16213e','#e2c044','#f4d03f','#fff9c4'] },
    WindSpeed:           { name: 'Wind Speed', icon: '💨', unit: 'm/s', colors: ['#f7fbff','#c6dbef','#6baed6','#2171b5','#08519c','#08306b'] },
    Humidity:            { name: 'Relative Humidity', icon: '🌫️', unit: '%', colors: ['#fff5eb','#fdd0a2','#fd8d3c','#d94801','#7f2704','#3f0000'] },
    SolarRadiation:      { name: 'Solar Radiation', icon: '☀️', unit: 'W/m²', colors: ['#023858','#0570b0','#74a9cf','#bdc9e1','#f1eef6','#f7fcf0'] },
    UHI_Intensity:       { name: 'UHI Intensity', icon: '🏙️', unit: '°C', colors: ['#2166ac','#67a9cf','#fddbc7','#ef8a62','#d6604d','#b2182b'] },
    UTFVI:               { name: 'UTFVI', icon: '📊', unit: 'index', colors: ['#2166ac','#92c5de','#f7f7f7','#f4a582','#d6604d','#b2182b'] },
};

const HEAT_COLORS = { Low: '#2166ac', Moderate: '#f59e0b', High: '#f97316', Extreme: '#ef4444' };

// ═══════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
    setLoader('Connecting to server...');
    try {
        const res = await fetch(`${API}/config`);
        config = await res.json();
    } catch (e) {
        setLoader('Cannot reach API server. Is backend/app.py running?');
        return;
    }

    // Update stats
    document.getElementById('stat-total').textContent = config.total_pixels?.toLocaleString() || '—';
    document.getElementById('stat-hotspots').textContent = config.hotspots?.toLocaleString() || '—';
    document.getElementById('stat-model').textContent = config.model_name || '—';

    // Check API key
    let apiKey = config.maps_api_key;
    if (!apiKey) {
        document.getElementById('loading-overlay').classList.add('hide');
        document.getElementById('apikey-modal').classList.remove('hidden');
        return;
    }

    loadGoogleMaps(apiKey);
});

function applyTempKey() {
    const key = document.getElementById('apikey-input').value.trim();
    if (!key) return;
    document.getElementById('apikey-modal').classList.add('hidden');
    document.getElementById('loading-overlay').classList.remove('hide');
    loadGoogleMaps(key);
}

function loadGoogleMaps(apiKey) {
    setLoader('Loading Google Maps...');
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=visualization,places&callback=onMapsReady`;
    script.async = true;
    script.defer = true;
    script.onerror = () => setLoader('Failed to load Google Maps. Check API key.');
    document.head.appendChild(script);
}

window.onMapsReady = async function () {
    setLoader('Initializing map...');
    initMap();
    initSearch();
    initUIBindings();
    buildLayerList();

    setLoader('Loading grid data (may take a moment)...');
    await loadGridData();

    renderGrid();
    updateLegend();

    document.getElementById('badge-status').innerHTML = '<span class="dot dot-ok"></span>Connected';
    document.getElementById('loading-overlay').classList.add('hide');

    // Expand simulator
    document.getElementById('simulator-bar').classList.add('expanded');
};

// ═══════════════════════════════════════════════════════════════
//  MAP INIT
// ═══════════════════════════════════════════════════════════════
function initMap() {
    const center = config.center || { lat: 28.6139, lng: 77.209 };
    map = new google.maps.Map(document.getElementById('map'), {
        center: center,
        zoom: config.zoom || 12,
        mapTypeId: 'roadmap',
        mapTypeControl: false,
        streetViewControl: true,
        fullscreenControl: true,
        fullscreenControlOptions: { position: google.maps.ControlPosition.RIGHT_TOP },
        zoomControl: true,
        zoomControlOptions: { position: google.maps.ControlPosition.RIGHT_CENTER },
        streetViewControlOptions: { position: google.maps.ControlPosition.RIGHT_CENTER },
        gestureHandling: 'greedy',
        styles: MAP_DARK_STYLE,
    });

    infoWindow = new google.maps.InfoWindow();

    // Fit to data bounds
    if (config.bounds) {
        const b = config.bounds;
        map.fitBounds(new google.maps.LatLngBounds(
            { lat: b.south, lng: b.west },
            { lat: b.north, lng: b.east }
        ));
    }
}

// ═══════════════════════════════════════════════════════════════
//  SEARCH (Places API)
// ═══════════════════════════════════════════════════════════════
function initSearch() {
    const input = document.getElementById('search-input');

    // Autocomplete with Places API
    searchBox = new google.maps.places.SearchBox(input);

    searchBox.addListener('places_changed', () => {
        const places = searchBox.getPlaces();
        if (!places || places.length === 0) return;
        const place = places[0];
        if (place.geometry && place.geometry.location) {
            map.panTo(place.geometry.location);
            map.setZoom(15);
        }
    });

    // Support raw lat/lng, pincode entry
    input.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        const val = input.value.trim();

        // Check for lat,lng pattern
        const llMatch = val.match(/^(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)$/);
        if (llMatch) {
            const lat = parseFloat(llMatch[1]);
            const lng = parseFloat(llMatch[2]);
            map.panTo({ lat, lng });
            map.setZoom(16);
            new google.maps.Marker({ position: { lat, lng }, map, animation: google.maps.Animation.DROP });
            return;
        }

        // Pincode → geocode
        if (/^\d{5,6}$/.test(val)) {
            const geocoder = new google.maps.Geocoder();
            geocoder.geocode({ address: val + ', India' }, (results, status) => {
                if (status === 'OK' && results[0]) {
                    map.panTo(results[0].geometry.location);
                    map.setZoom(14);
                }
            });
        }
    });
}

// ═══════════════════════════════════════════════════════════════
//  UI BINDINGS
// ═══════════════════════════════════════════════════════════════
function initUIBindings() {
    // View type buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            map.setMapTypeId(btn.dataset.type);
        });
    });

    // Opacity slider
    const opSlider = document.getElementById('opacity-slider');
    opSlider.addEventListener('input', () => {
        gridOpacity = parseInt(opSlider.value) / 100;
        document.getElementById('opacity-val').textContent = opSlider.value + '%';
        updateGridOpacity();
    });

    // Simulator sliders
    const simSliders = [
        { id: 's-tree', val: 'sv-tree', suffix: '%' },
        { id: 's-greenroof', val: 'sv-greenroof', suffix: '%' },
        { id: 's-coolroof', val: 'sv-coolroof', suffix: '%' },
        { id: 's-water', val: 'sv-water', suffix: '%' },
        { id: 's-albedo', val: 'sv-albedo', suffix: '', fmt: v => (v / 100).toFixed(2) },
        { id: 's-imperv', val: 'sv-imperv', suffix: '%' },
        { id: 's-bldg', val: 'sv-bldg', suffix: '%' },
    ];
    simSliders.forEach(s => {
        const el = document.getElementById(s.id);
        if (!el) return;
        el.addEventListener('input', () => {
            document.getElementById(s.val).textContent =
                s.fmt ? s.fmt(el.value) : el.value + s.suffix;
        });
    });

    // Sim view selector
    document.getElementById('sim-view').addEventListener('change', (e) => {
        simView = e.target.value;
        if (scenarioData) renderGrid();
    });
}

// ═══════════════════════════════════════════════════════════════
//  LAYER LIST
// ═══════════════════════════════════════════════════════════════
function buildLayerList() {
    const container = document.getElementById('layer-list');
    container.innerHTML = '';
    for (const [key, def] of Object.entries(LAYERS)) {
        const item = document.createElement('div');
        item.className = 'layer-item' + (key === currentLayer ? ' active' : '');
        item.dataset.layer = key;
        item.innerHTML = `<span class="layer-dot" style="background:${def.colors[4]}"></span>${def.icon} ${def.name}`;
        item.addEventListener('click', () => {
            document.querySelectorAll('.layer-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            currentLayer = key;
            renderGrid();
            updateLegend();
        });
        container.appendChild(item);
    }
}

// ═══════════════════════════════════════════════════════════════
//  DATA LOADING
// ═══════════════════════════════════════════════════════════════
async function loadGridData() {
    try {
        const res = await fetch(`${API}/grid`);
        const data = await res.json();
        gridPixels = data.pixels || [];
        gridStats = data.stats || {};
    } catch (e) {
        console.error('Failed to load grid data:', e);
        setLoader('Failed to load grid data. Check backend.');
    }
}

// ═══════════════════════════════════════════════════════════════
//  GRID RENDERING (Rectangles)
// ═══════════════════════════════════════════════════════════════
function renderGrid() {
    // Clear existing
    clearGrid();

    if (!gridPixels.length) return;

    const halfLat = (config.pixel_size_deg || 0.00027) / 2;
    const halfLng = halfLat * 1.14; // cos(28.5°) correction

    const batches = chunkArray(gridPixels, 200);
    let batchIdx = 0;

    function renderBatch() {
        if (batchIdx >= batches.length) return;
        const batch = batches[batchIdx++];

        for (const px of batch) {
            const val = getPixelValue(px);
            const color = getColor(val, currentLayer);

            const rect = new google.maps.Rectangle({
                bounds: {
                    north: px.Latitude + halfLat,
                    south: px.Latitude - halfLat,
                    east: px.Longitude + halfLng,
                    west: px.Longitude - halfLng,
                },
                strokeColor: 'transparent',
                strokeOpacity: 0,
                strokeWeight: 0,
                fillColor: color,
                fillOpacity: gridOpacity,
                map: map,
                clickable: true,
                zIndex: 1,
            });

            rect._pixelData = px;

            rect.addListener('click', (e) => {
                onPixelClick(px, e.latLng);
            });

            rect.addListener('mouseover', () => {
                rect.setOptions({ strokeColor: '#ffffff', strokeOpacity: 0.8, strokeWeight: 1.5, zIndex: 10 });
            });
            rect.addListener('mouseout', () => {
                rect.setOptions({ strokeColor: 'transparent', strokeOpacity: 0, strokeWeight: 0, zIndex: 1 });
            });

            gridRectangles.push(rect);
        }

        // Render next batch asynchronously for smooth UX
        if (batchIdx < batches.length) {
            requestAnimationFrame(renderBatch);
        }
    }

    renderBatch();
}

function clearGrid() {
    gridRectangles.forEach(r => r.setMap(null));
    gridRectangles = [];
}

function updateGridOpacity() {
    gridRectangles.forEach(r => r.setOptions({ fillOpacity: gridOpacity }));
}

function getPixelValue(px) {
    if (simView === 'after' && scenarioData) {
        const sp = scenarioData.pixelMap[px.PixelID];
        return sp ? sp.a : (px[currentLayer] || 0);
    }
    if (simView === 'diff' && scenarioData) {
        const sp = scenarioData.pixelMap[px.PixelID];
        return sp ? sp.d : 0;
    }
    return px[currentLayer] || 0;
}

// ═══════════════════════════════════════════════════════════════
//  COLOR INTERPOLATION
// ═══════════════════════════════════════════════════════════════
function getColor(value, layerKey) {
    const stats = gridStats[layerKey];
    if (!stats) return '#333333';

    const def = LAYERS[layerKey];
    const colors = def ? def.colors : ['#2166ac', '#f7f7f7', '#b2182b'];

    // Diff mode uses diverging scale centered on 0
    if (simView === 'diff' && scenarioData) {
        const maxAbs = Math.max(Math.abs(stats.min), Math.abs(stats.max), 5);
        const t = (value + maxAbs) / (2 * maxAbs);
        return interpolateColors(['#2166ac', '#67a9cf', '#f7f7f7', '#ef8a62', '#b2182b'], clamp01(t));
    }

    let t = (value - stats.min) / (stats.max - stats.min || 1);
    t = clamp01(t);
    return interpolateColors(colors, t);
}

function interpolateColors(palette, t) {
    const n = palette.length - 1;
    const idx = t * n;
    const lo = Math.floor(idx);
    const hi = Math.min(lo + 1, n);
    const frac = idx - lo;
    return lerpColor(palette[lo], palette[hi], frac);
}

function lerpColor(c1, c2, t) {
    const r1 = parseInt(c1.slice(1, 3), 16), g1 = parseInt(c1.slice(3, 5), 16), b1 = parseInt(c1.slice(5, 7), 16);
    const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);
    return `#${hex(r)}${hex(g)}${hex(b)}`;
}

function hex(n) { return n.toString(16).padStart(2, '0'); }
function clamp01(v) { return Math.max(0, Math.min(1, v)); }
function chunkArray(arr, size) {
    const chunks = [];
    for (let i = 0; i < arr.length; i += size) chunks.push(arr.slice(i, i + size));
    return chunks;
}

// ═══════════════════════════════════════════════════════════════
//  LEGEND
// ═══════════════════════════════════════════════════════════════
function updateLegend() {
    const container = document.getElementById('legend-container');
    const def = LAYERS[currentLayer];
    const stats = gridStats[currentLayer];
    if (!def || !stats) { container.innerHTML = ''; return; }

    const gradient = def.colors.join(', ');
    let title = def.name;
    if (simView === 'diff' && scenarioData) title += ' (Difference)';

    container.innerHTML = `
        <div class="legend-title">${title} (${def.unit})</div>
        <div class="legend-bar" style="background:linear-gradient(90deg,${gradient})"></div>
        <div class="legend-labels">
            <span>${stats.min.toFixed(1)}</span>
            <span>${stats.mean.toFixed(1)}</span>
            <span>${stats.max.toFixed(1)}</span>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════
//  PIXEL CLICK → DETAIL PANEL
// ═══════════════════════════════════════════════════════════════
async function onPixelClick(px, latLng) {
    selectedPixel = px;

    // Show quick info window on map
    const cls = px.HeatClass_Label || 'Unknown';
    infoWindow.setContent(`
        <div style="font-family:Inter,sans-serif;color:#1e293b;min-width:160px">
            <div style="font-weight:800;font-size:14px;margin-bottom:4px">
                Heat Score: ${(px.HeatScore_Predicted || 0).toFixed(1)}
            </div>
            <div style="font-size:12px;color:#64748b">
                LST: ${(px.LST || 0).toFixed(1)}°C · Class: ${cls}<br>
                Pixel #${px.PixelID}
            </div>
            <div style="font-size:11px;color:#94a3b8;margin-top:4px">Loading details...</div>
        </div>
    `);
    infoWindow.setPosition(latLng);
    infoWindow.open(map);

    // Open detail panel
    const panel = document.getElementById('detail-panel');
    panel.classList.remove('hidden');

    // Load detailed data
    try {
        const res = await fetch(`${API}/pixel/${px.PixelID}`);
        const data = await res.json();
        renderDetailPanel(data);

        // Update info window
        infoWindow.setContent(`
            <div style="font-family:Inter,sans-serif;color:#1e293b;min-width:180px">
                <div style="font-weight:800;font-size:14px;margin-bottom:4px">
                    Heat Score: ${data.heat_score.toFixed(1)} · ${data.heat_class}
                </div>
                <div style="font-size:12px;color:#475569">
                    LST: ${data.lst.toFixed(1)}°C · Air: ${data.air_temp.toFixed(1)}°C<br>
                    Priority: ${data.priority} · Confidence: ${(data.confidence * 100).toFixed(0)}%
                </div>
            </div>
        `);
    } catch (e) {
        console.error('Pixel detail error:', e);
    }
}

function renderDetailPanel(data) {
    const body = document.getElementById('detail-body');
    const cls = (data.heat_class || 'Unknown').toLowerCase();
    const badgeCls = `badge-${cls}`;

    // Features table rows
    const featureRows = Object.entries(data.features || {}).map(([k, v]) => `
        <div class="detail-row">
            <span class="label">${k.replace(/_/g, ' ')}</span>
            <span class="value">${typeof v === 'number' ? v.toFixed(4) : v}</span>
        </div>
    `).join('');

    // Top drivers
    const driverRows = (data.top_drivers || []).map(d => `
        <div style="margin-bottom:6px">
            <div class="detail-row">
                <span class="label">${d.feature.replace(/_/g, ' ')}</span>
                <span class="value" style="color:${d.direction === 'heating' ? 'var(--heat)' : 'var(--cool)'}">
                    ${d.contribution_pct.toFixed(1)}% ${d.direction === 'heating' ? '↑' : '↓'}
                </span>
            </div>
            <div class="driver-bar ${d.direction === 'heating' ? 'driver-heat' : 'driver-cool'}"
                 style="width:${Math.min(d.contribution_pct, 100)}%"></div>
        </div>
    `).join('');

    // SHAP-like contributions (top 8)
    const contribs = Object.entries(data.contributions || {}).slice(0, 8);
    const shapRows = contribs.map(([k, v]) => `
        <div class="detail-row">
            <span class="label">${k.replace(/_/g, ' ')}</span>
            <span class="value">${v.toFixed(1)}%</span>
        </div>
    `).join('');

    body.innerHTML = `
        <!-- Score -->
        <div class="detail-section">
            <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:6px">
                <span class="detail-score" style="color:${HEAT_COLORS[data.heat_class] || '#fff'}">${data.heat_score.toFixed(1)}</span>
                <span class="detail-badge ${badgeCls}">${data.heat_class}</span>
            </div>
            <div class="detail-row"><span class="label">LST</span><span class="value">${data.lst.toFixed(1)}°C</span></div>
            <div class="detail-row"><span class="label">Air Temp</span><span class="value">${data.air_temp.toFixed(1)}°C</span></div>
            <div class="detail-row"><span class="label">Priority</span><span class="value" style="color:${data.priority === 'Critical' ? 'var(--heat)' : data.priority === 'High' ? 'var(--orange)' : 'var(--txt2)'}">${data.priority}</span></div>
            <div class="detail-row"><span class="label">Confidence</span><span class="value">${(data.confidence * 100).toFixed(0)}%</span></div>
            <div class="detail-row"><span class="label">Pixel ID</span><span class="value">#${data.pixel_id}</span></div>
            <div class="detail-row"><span class="label">Location</span><span class="value">${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}</span></div>
        </div>

        <!-- Top Heat Drivers -->
        <div class="detail-section">
            <div class="detail-title">🔥 Dominant Heat Drivers</div>
            ${driverRows || '<div class="detail-row"><span class="label">No significant drivers</span></div>'}
        </div>

        <!-- SHAP Feature Importance -->
        <div class="detail-section">
            <div class="detail-title">📊 Feature Importance (SHAP)</div>
            ${shapRows}
        </div>

        <!-- Cooling Recommendation -->
        <div class="detail-section">
            <div class="detail-title">🌿 Recommended Cooling Strategy</div>
            <div class="rec-text">${data.recommendation.replace(/\|/g, '<br>• ')}</div>
        </div>

        <!-- Predicted Reduction -->
        <div class="detail-section">
            <div class="detail-title">📉 Predicted Reduction</div>
            <div class="detail-row"><span class="label">Temperature Δ</span><span class="value" style="color:var(--green)">-${data.predicted_reduction.toFixed(2)}°C</span></div>
            <div class="detail-row"><span class="label">Cost Estimate</span><span class="value">₹${(data.cost_estimate / 100000).toFixed(1)}L</span></div>
        </div>

        <!-- Feature Values (collapsible) -->
        <div class="detail-section">
            <div class="detail-title" style="cursor:pointer" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display==='none'?'block':'none'">
                📋 All Feature Values ▸
            </div>
            <div style="display:none;max-height:300px;overflow-y:auto">${featureRows}</div>
        </div>
    `;
}

function closeDetailPanel() {
    document.getElementById('detail-panel').classList.add('hidden');
    selectedPixel = null;
    if (infoWindow) infoWindow.close();
}

// ═══════════════════════════════════════════════════════════════
//  SCENARIO SIMULATOR
// ═══════════════════════════════════════════════════════════════
async function runSpatialPrediction() {
    const btn = document.getElementById('btn-sim');
    btn.classList.add('loading');
    btn.textContent = '⏳ Computing...';

    const params = {
        tree_cover_pct: parseFloat(document.getElementById('s-tree').value),
        cool_roof_pct: parseFloat(document.getElementById('s-coolroof').value),
        green_roof_pct: parseFloat(document.getElementById('s-greenroof').value),
        water_body_pct: parseFloat(document.getElementById('s-water').value),
        albedo_change: parseFloat(document.getElementById('s-albedo').value) / 100,
        impervious_reduction_pct: parseFloat(document.getElementById('s-imperv').value),
        building_density_reduction_pct: parseFloat(document.getElementById('s-bldg').value),
    };

    try {
        const res = await fetch(`${API}/predict/spatial`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        const data = await res.json();
        if (data.error) { alert('Error: ' + data.error); return; }

        // Build pixel lookup map
        const pixelMap = {};
        (data.pixels || []).forEach(p => pixelMap[p.id] = p);
        scenarioData = { ...data, pixelMap };

        // Update KPIs
        const s = data.summary;
        document.getElementById('kpi-before').textContent = `Before: ${s.before_mean}`;
        document.getElementById('kpi-after').textContent = `After: ${s.after_mean}`;
        document.getElementById('kpi-reduction').textContent = `Δ ${s.reduction} (${s.reduction_pct}%)`;

        // Switch to "after" view and re-render
        simView = 'after';
        document.getElementById('sim-view').value = 'after';
        renderGrid();

    } catch (e) {
        console.error('Spatial prediction failed:', e);
        alert('Could not reach API. Is backend running?');
    } finally {
        btn.classList.remove('loading');
        btn.textContent = '⚡ Predict';
    }
}

function resetSimulator() {
    // Reset sliders
    ['s-tree', 's-greenroof', 's-coolroof', 's-water', 's-albedo', 's-imperv', 's-bldg'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = 0;
    });
    ['sv-tree', 'sv-greenroof', 'sv-coolroof', 'sv-water', 'sv-imperv', 'sv-bldg'].forEach(id => {
        document.getElementById(id).textContent = '0%';
    });
    document.getElementById('sv-albedo').textContent = '0.00';

    // Reset state
    scenarioData = null;
    simView = 'before';
    document.getElementById('sim-view').value = 'before';
    document.getElementById('kpi-before').textContent = 'Before: —';
    document.getElementById('kpi-after').textContent = 'After: —';
    document.getElementById('kpi-reduction').textContent = 'Δ: —';

    renderGrid();
}

// ═══════════════════════════════════════════════════════════════
//  PANEL TOGGLING
// ═══════════════════════════════════════════════════════════════
function togglePanel(panelId) {
    const el = document.getElementById(panelId);
    if (panelId === 'sidebar') {
        el.classList.toggle('collapsed');
    } else if (panelId === 'simulator-bar') {
        el.classList.toggle('expanded');
    }
}

// ═══════════════════════════════════════════════════════════════
//  EXPORT
// ═══════════════════════════════════════════════════════════════
function exportPNG() {
    // Use html2canvas-like approach with map static image
    const link = document.createElement('a');
    const canvas = document.querySelector('#map canvas');
    if (canvas) {
        link.href = canvas.toDataURL('image/png');
        link.download = `urban_heat_map_${Date.now()}.png`;
        link.click();
    } else {
        // Fallback: use Google Static Maps
        const center = map.getCenter();
        const zoom = map.getZoom();
        const url = `https://maps.googleapis.com/maps/api/staticmap?center=${center.lat()},${center.lng()}&zoom=${zoom}&size=1280x720&maptype=${map.getMapTypeId()}&key=${config.maps_api_key}`;
        window.open(url, '_blank');
    }
}

function exportGeoJSON() {
    const features = gridPixels.map(px => ({
        type: 'Feature',
        properties: {
            PixelID: px.PixelID,
            HeatScore: px.HeatScore_Predicted,
            HeatClass: px.HeatClass_Label,
            LST: px.LST,
            NDVI: px.NDVI,
            NDBI: px.NDBI,
            UHI_Intensity: px.UHI_Intensity,
        },
        geometry: {
            type: 'Point',
            coordinates: [px.Longitude, px.Latitude],
        },
    }));

    const geojson = { type: 'FeatureCollection', features };
    downloadJSON(geojson, `urban_heat_${Date.now()}.geojson`);
}

function exportCSV() {
    if (!gridPixels.length) return;
    const keys = Object.keys(gridPixels[0]);
    const csv = [keys.join(',')];
    gridPixels.forEach(px => {
        csv.push(keys.map(k => {
            const v = px[k];
            return typeof v === 'string' ? `"${v}"` : v;
        }).join(','));
    });
    downloadText(csv.join('\n'), `urban_heat_${Date.now()}.csv`, 'text/csv');
}

function downloadJSON(obj, filename) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
}

function downloadText(text, filename, type) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
}

// ═══════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════
function setLoader(text) {
    const el = document.getElementById('loader-text');
    if (el) el.textContent = text;
}

// ═══════════════════════════════════════════════════════════════
//  GOOGLE MAPS DARK STYLE
// ═══════════════════════════════════════════════════════════════
const MAP_DARK_STYLE = [
    { elementType: 'geometry', stylers: [{ color: '#1d2c4d' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#8ec3b9' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#1a3646' }] },
    { featureType: 'administrative.country', elementType: 'geometry.stroke', stylers: [{ color: '#4b6878' }] },
    { featureType: 'administrative.province', elementType: 'geometry.stroke', stylers: [{ color: '#4b6878' }] },
    { featureType: 'landscape', elementType: 'geometry', stylers: [{ color: '#0e1626' }] },
    { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#283d6a' }] },
    { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#6f9ba5' }] },
    { featureType: 'poi.park', elementType: 'geometry.fill', stylers: [{ color: '#023e58' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#304a7d' }] },
    { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#98a5be' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#2c6675' }] },
    { featureType: 'transit', elementType: 'labels.text.fill', stylers: [{ color: '#98a5be' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e1626' }] },
    { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#4e6d70' }] },
];
