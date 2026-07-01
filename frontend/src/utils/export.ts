import type { GridPixel } from '../types';

export function exportGeoJSON(pixels: GridPixel[]) {
  const fc = {
    type: 'FeatureCollection' as const,
    features: pixels.map((px) => ({
      type: 'Feature' as const,
      properties: { PixelID: px.PixelID, HeatScore: px.HeatScore_Predicted, HeatClass: px.HeatClass_Label, LST: px.LST, NDVI: px.NDVI, UHI: px.UHI_Intensity },
      geometry: { type: 'Point' as const, coordinates: [px.Longitude, px.Latitude] },
    })),
  };
  download(JSON.stringify(fc, null, 2), `urban_heat_${Date.now()}.geojson`, 'application/json');
}

export function exportCSV(pixels: GridPixel[]) {
  if (!pixels.length) return;
  const keys = Object.keys(pixels[0]);
  const rows = [keys.join(',')];
  pixels.forEach((px) => {
    rows.push(keys.map((k) => { const v = px[k]; return typeof v === 'string' ? `"${v}"` : v; }).join(','));
  });
  download(rows.join('\n'), `urban_heat_${Date.now()}.csv`, 'text/csv');
}

export function exportPNG(canvas: HTMLCanvasElement | null) {
  if (!canvas) return;
  const link = document.createElement('a');
  link.href = canvas.toDataURL('image/png');
  link.download = `urban_heat_map_${Date.now()}.png`;
  link.click();
}

function download(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
