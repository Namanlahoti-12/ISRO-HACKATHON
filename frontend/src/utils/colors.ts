import type { StatsEntry } from '../types';
import { getLayerDef } from '../maps/layerConfig';

export function getColor(
  value: number,
  layerKey: string,
  stats: Record<string, StatsEntry>,
  isDiff = false,
): string {
  const st = stats?.[layerKey];

  // No stats available — use a visible mid-range color based on layer palette
  if (!st) {
    const def = getLayerDef(layerKey);
    const palette = def?.colors ?? ['#2166ac', '#f7f7f7', '#b2182b'];
    return palette[Math.floor(palette.length / 2)];
  }

  if (isDiff) {
    const maxAbs = Math.max(Math.abs(st.min), Math.abs(st.max), 0.01);
    const t = clamp01((value + maxAbs) / (2 * maxAbs));
    return interpolate(['#2166ac', '#67a9cf', '#f7f7f7', '#ef8a62', '#b2182b'], t);
  }

  const def = getLayerDef(layerKey);
  const palette = def?.colors ?? ['#2166ac', '#f7f7f7', '#b2182b'];

  // LULC_Derived uses categorical colors (0–3)
  if (layerKey === 'LULC_Derived') {
    const classColors = ['#006400', '#808080', '#0000CD', '#D3D3D3'];
    const idx = Math.min(Math.round(value), 3);
    return classColors[idx] ?? classColors[0];
  }

  const range = st.max - st.min;
  // If all values are identical (range=0) → mid palette color
  const t = range < 0.0001 ? 0.5 : clamp01((value - st.min) / range);
  return interpolate(palette, t);
}

export function interpolate(palette: string[], t: number): string {
  if (palette.length === 1) return palette[0];
  const n = palette.length - 1;
  const idx = t * n;
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, n);
  return lerp(palette[lo], palette[hi], idx - lo);
}

function lerp(c1: string, c2: string, t: number): string {
  const [r1, g1, b1] = hex2rgb(c1);
  const [r2, g2, b2] = hex2rgb(c2);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `#${hex(r)}${hex(g)}${hex(b)}`;
}

function hex2rgb(c: string): [number, number, number] {
  const s = c.replace('#', '');
  return [
    parseInt(s.slice(0, 2), 16),
    parseInt(s.slice(2, 4), 16),
    parseInt(s.slice(4, 6), 16),
  ];
}

function hex(n: number) { return n.toString(16).padStart(2, '0'); }
function clamp01(v: number) { return Math.max(0, Math.min(1, v)); }

/* ── CSS gradient string for legend ── */
export function gradientCSS(colors: string[]): string {
  return `linear-gradient(90deg, ${colors.join(', ')})`;
}

/**
 * Build a MapLibre GL data-driven fill-color expression.
 * Reads the raw numeric value from feature properties (via ['get', layerKey])
 * and maps it to the layer's palette using GPU-side linear interpolation.
 *
 * This is the proper GIS approach used by GEE, ArcGIS, and QGIS:
 * color = f(data_value) computed at render time, not pre-baked into the data.
 */
export function buildFillColorExpression(
  layerKey: string,
  stats: Record<string, { min: number; max: number }>,
  palette: string[],
): unknown[] {
  // LULC uses categorical match expression
  if (layerKey === 'LULC_Derived') {
    return [
      'match', ['to-number', ['get', 'LULC_Derived'], 3],
      0, '#15803d',  // Vegetation — dark green
      1, '#71717a',  // Built-up  — grey
      2, '#1d4ed8',  // Water     — blue
      '#d97706',     // Bare/Other — amber
    ];
  }

  const st = stats?.[layerKey];
  const mid = palette[Math.floor(palette.length / 2)];

  if (!st) return [mid]; // no stats → flat mid colour (still visible)

  const { min, max } = st;
  const range = max - min;

  if (range < 0.0001) return [mid]; // constant field → flat colour

  // Build [value, color, ...] pairs spread evenly across [min, max]
  const n = palette.length;
  const stops: unknown[] = [];
  palette.forEach((color, i) => {
    const val = min + (i / (n - 1)) * range;
    stops.push(val, color);
  });

  // ['interpolate', ['linear'], ['get', key], stop0, color0, stop1, color1, ...]
  return ['interpolate', ['linear'], ['get', layerKey], ...stops];
}
