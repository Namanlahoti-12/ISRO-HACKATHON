import type { LayerDef } from '../types';
import type { StyleSpecification } from 'maplibre-gl';

/* ── All 28 Data Layers ── */
export const LAYERS: LayerDef[] = [
  // ── Primary AI Output ──
  {
    key: 'HeatScore_Predicted',
    name: 'AI Heat Score',
    icon: '🌡️',
    unit: '°C',
    group: 'ai',
    colors: ['#0000ff','#00ffff','#00ff00','#ffff00','#ff8000','#ff0000','#800000'],
  },

  // ── Thermal ──
  {
    key: 'LST',
    name: 'Land Surface Temp',
    icon: '🔥',
    unit: '°C',
    group: 'thermal',
    colors: ['#0000ff','#00ffff','#00ff00','#ffff00','#ff8000','#ff0000','#800000'],
  },
  {
    key: 'AirTemp',
    name: 'Air Temperature',
    icon: '🌡',
    unit: '°C',
    group: 'thermal',
    colors: ['#2563eb','#67e8f9','#fef08a','#fb923c','#dc2626'],
  },
  {
    key: 'UHI_Intensity',
    name: 'UHI Intensity',
    icon: '🏙️',
    unit: '°C',
    group: 'thermal',
    colors: ['#1d4ed8','#22c55e','#facc15','#f97316','#dc2626'],
  },
  {
    key: 'UTCI_Approx',
    name: 'UTCI (Thermal Comfort)',
    icon: '🧍',
    unit: '°C',
    group: 'thermal',
    colors: ['#1e40af','#06b6d4','#facc15','#f97316','#b91c1c'],
  },
  {
    key: 'UTFVI',
    name: 'UTFVI',
    icon: '📊',
    unit: 'idx',
    group: 'thermal',
    colors: ['#1d4ed8','#22c55e','#facc15','#dc2626'],
  },

  // ── Spectral Indices ──
  {
    key: 'NDVI',
    name: 'NDVI (Vegetation)',
    icon: '🌿',
    unit: '-1→1',
    group: 'indices',
    colors: ['#7c2d12','#facc15','#bbf7d0','#22c55e','#14532d'],
  },
  {
    key: 'NDBI',
    name: 'NDBI (Built-up)',
    icon: '🏗️',
    unit: '-1→1',
    group: 'indices',
    colors: ['#fef9c3','#fb923c','#dc2626'],
  },
  {
    key: 'NDWI',
    name: 'NDWI (Water)',
    icon: '💧',
    unit: '-1→1',
    group: 'indices',
    colors: ['#ffffff','#bfdbfe','#2563eb','#1e3a8a'],
  },
  {
    key: 'MNDWI',
    name: 'MNDWI',
    icon: '🌊',
    unit: '-1→1',
    group: 'indices',
    colors: ['#e0f2fe','#60a5fa','#1d4ed8'],
  },

  // ── Land Use / Cover ──
  {
    key: 'LULC_Derived',
    name: 'LULC (Derived)',
    icon: '🗺️',
    unit: 'class',
    group: 'landuse',
    colors: ['#14532d','#d95f0e','#1d4ed8','#d1d5db'],
  },

  // ── Population & Built Environment ──
  {
    key: 'Population_Density',
    name: 'Population Density',
    icon: '👥',
    unit: 'ppl/px',
    group: 'urban',
    colors: ['#fef9c3','#fb923c','#dc2626'],
  },
  {
    key: 'Building_Density',
    name: 'Building Density',
    icon: '🏢',
    unit: '%',
    group: 'urban',
    colors: ['#9ca3af','#fb923c','#dc2626'],
  },
  {
    key: 'Building_Height',
    name: 'Building Height',
    icon: '🏗️',
    unit: 'm',
    group: 'urban',
    colors: ['#e5e7eb','#facc15','#f97316','#7f1d1d'],
  },
  {
    key: 'Road_Density_Proxy',
    name: 'Road Density',
    icon: '🛣️',
    unit: 'idx',
    group: 'urban',
    colors: ['#d1d5db','#f97316','#b91c1c'],
  },
  {
    key: 'Anthropogenic_Heat',
    name: 'Anthropogenic Heat',
    icon: '🏭',
    unit: 'W/m²',
    group: 'urban',
    colors: ['#fef9c3','#fb923c','#dc2626','#7f1d1d'],
  },
  {
    key: 'Nighttime_Lights',
    name: 'Night-time Lights',
    icon: '🌃',
    unit: 'nW',
    group: 'urban',
    colors: ['#2e1065','#7e22ce','#facc15'],
  },
  {
    key: 'Impervious_Frac',
    name: 'Impervious Surface',
    icon: '🧱',
    unit: '0–1',
    group: 'urban',
    colors: ['#9ca3af','#fb923c','#dc2626'],
  },

  // ── Vegetation & Water ──
  {
    key: 'Tree_Cover_Pct',
    name: 'Tree Cover',
    icon: '🌳',
    unit: '%',
    group: 'nature',
    colors: ['#bbf7d0','#22c55e','#14532d'],
  },
  {
    key: 'Dist_Water',
    name: 'Distance to Water',
    icon: '🏞️',
    unit: 'm',
    group: 'nature',
    colors: ['#1d4ed8','#bfdbfe','#ffffff'],
  },
  {
    key: 'Dist_Green',
    name: 'Distance to Green',
    icon: '🌱',
    unit: 'm',
    group: 'nature',
    colors: ['#14532d','#bbf7d0','#ffffff'],
  },
  {
    key: 'Green_Space_Density',
    name: 'Green Space Density',
    icon: '🏡',
    unit: '0–1',
    group: 'nature',
    colors: ['#dcfce7','#22c55e','#14532d'],
  },
  {
    key: 'Albedo',
    name: 'Surface Albedo',
    icon: '🪞',
    unit: '0–1',
    group: 'nature',
    colors: ['#111827','#6b7280','#d1d5db','#ffffff'],
  },

  // ── Meteorology ──
  {
    key: 'Humidity',
    name: 'Relative Humidity',
    icon: '🌫️',
    unit: '%',
    group: 'meteo',
    colors: ['#facc15','#22c55e','#1d4ed8'],
  },
  {
    key: 'WindSpeed',
    name: 'Wind Speed',
    icon: '💨',
    unit: 'm/s',
    group: 'meteo',
    colors: ['#7e22ce','#2563eb','#06b6d4'],
  },
  {
    key: 'WindDirection',
    name: 'Wind Direction',
    icon: '🧭',
    unit: '°',
    group: 'meteo',
    colors: ['#7e22ce','#facc15','#06b6d4','#22c55e'],
  },
  {
    key: 'SolarRadiation',
    name: 'Solar Radiation',
    icon: '☀️',
    unit: 'W/m²',
    group: 'meteo',
    colors: ['#facc15','#fb923c','#dc2626'],
  },

  // ── Topography ──
  {
    key: 'Elevation',
    name: 'Elevation',
    icon: '⛰️',
    unit: 'm',
    group: 'topo',
    colors: ['#166534','#facc15','#a16207','#78716c'],
  },
];

export const LAYER_GROUPS: Record<string, string> = {
  ai:      '🤖 AI Output',
  thermal: '🌡️ Thermal',
  indices: '📡 Spectral Indices',
  landuse: '🗺️ Land Use',
  urban:   '🏙️ Urban',
  nature:  '🌿 Nature',
  meteo:   '⛅ Meteorology',
  topo:    '⛰️ Topography',
};

export const HEAT_COLORS: Record<string, string> = {
  Low: '#2166ac', Moderate: '#f59e0b', High: '#f97316', Extreme: '#ef4444',
};

/* ── Map Base Styles ── */
export const LIGHT_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty/style.json';
export const DARK_STYLE_URL  = 'https://tiles.openfreemap.org/styles/dark/style.json';

export const DARK_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'],
      tileSize: 256,
      attribution: '© CARTO © OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'carto-dark-layer', type: 'raster', source: 'carto-dark' }],
};

export const OSM_FALLBACK: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm-layer', type: 'raster', source: 'osm' }],
};

export function getLayerDef(key: string): LayerDef | undefined {
  return LAYERS.find((l) => l.key === key);
}

/**
 * Converts a layer's color palette into a MapLibre heatmap-color expression.
 * heatmap-density 0 = no data (transparent), 1 = maximum weight.
 * The palette is spread evenly across [0.001 → 1].
 */
export function getHeatmapColorExpression(layerKey: string): unknown[] {
  const def = getLayerDef(layerKey);
  const palette = def?.colors ?? [
    '#08306b','#2171b5','#22c55e','#facc15','#f97316','#ef4444','#7f1d1d',
  ];
  const n = palette.length;

  // Build [stop, color, stop, color, ...] pairs
  const pairs: unknown[] = [
    0,     'rgba(0,0,0,0)',    // fully transparent where there is no data
    0.001, palette[0],         // start of data range
  ];

  for (let i = 1; i < n; i++) {
    const stop = 0.001 + (i / (n - 1)) * 0.999; // maps i=0→0.001, i=n-1→1
    pairs.push(Math.min(stop, 1), palette[i]);
  }

  return ['interpolate', ['linear'], ['heatmap-density'], ...pairs];
}
