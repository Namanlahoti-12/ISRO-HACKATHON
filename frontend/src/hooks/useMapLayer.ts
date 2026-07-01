import { useCallback, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { useStore } from '../store/useStore';
import { getColor } from '../utils/colors';
import type { GridResponse, SpatialPrediction } from '../types';

export function useMapLayer() {
  const sourceReadyRef = useRef(false);

  const addGridSource = useCallback(
    (
      map: maplibregl.Map,
      gridData: GridResponse,
      layer: string,
      opacity: number,
      simView: string,
      spatialResult: SpatialPrediction | null,
      pixelSizeDeg: number,
      setSelectedPixelId: (id: number | null) => void,
      setDetailOpen: (open: boolean) => void,
    ) => {
      const halfLat = pixelSizeDeg / 2;
      const halfLng = halfLat * 1.14;

      const spMap = new Map<number, { a: number; d: number }>();
      if (spatialResult?.pixels) {
        for (const sp of spatialResult.pixels) {
          spMap.set(sp.id, sp);
        }
      }

      const features: GeoJSON.Feature[] = gridData.pixels.map((px) => {
        let val = (px[layer] as number) ?? 0;
        let isDiff = false;

        if (spMap.size > 0 && simView !== 'before') {
          const sp = spMap.get(px.PixelID);
          if (sp) {
            if (simView === 'after') val = sp.a;
            else { val = sp.d; isDiff = true; }
          }
        }

        return {
          type: 'Feature',
          properties: {
            id: px.PixelID,
            color: getColor(val, isDiff ? 'HeatScore_Predicted' : layer, gridData.stats, isDiff),
            value: Math.round(val * 100) / 100,
            label: px.HeatClass_Label ?? '',
            lat: px.Latitude,
            lng: px.Longitude,
          },
          geometry: {
            type: 'Polygon',
            coordinates: [[
              [px.Longitude - halfLng, px.Latitude - halfLat],
              [px.Longitude + halfLng, px.Latitude - halfLat],
              [px.Longitude + halfLng, px.Latitude + halfLat],
              [px.Longitude - halfLng, px.Latitude + halfLat],
              [px.Longitude - halfLng, px.Latitude - halfLat],
            ]],
          },
        };
      });

      const geojson: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features };

      if (map.getSource('grid')) {
        (map.getSource('grid') as maplibregl.GeoJSONSource).setData(geojson);
        if (map.getLayer('grid-fill')) {
          map.setPaintProperty('grid-fill', 'fill-opacity', opacity);
        }
        return;
      }

      map.addSource('grid', {
        type: 'geojson',
        data: geojson,
        generateId: true,
      });

      map.addLayer({
        id: 'grid-fill',
        type: 'fill',
        source: 'grid',
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], Math.min(opacity + 0.15, 1), opacity],
        },
      });

      map.addLayer({
        id: 'grid-line',
        type: 'line',
        source: 'grid',
        paint: { 'line-color': 'rgba(255,255,255,0.06)', 'line-width': 0.3 },
      });

      // Click handler
      map.on('click', 'grid-fill', (e) => {
        if (e.features?.length) {
          const props = e.features[0].properties;
          if (props?.id != null) {
            setSelectedPixelId(props.id);
            setDetailOpen(true);
          }
        }
      });

      // Hover effect
      let hoveredId: string | number | undefined;
      map.on('mousemove', 'grid-fill', (e) => {
        if (e.features?.length) {
          if (hoveredId !== undefined) {
            map.setFeatureState({ source: 'grid', id: hoveredId }, { hover: false });
          }
          hoveredId = e.features[0].id;
          map.setFeatureState({ source: 'grid', id: hoveredId! }, { hover: true });
          map.getCanvas().style.cursor = 'crosshair';
        }
      });

      map.on('mouseleave', 'grid-fill', () => {
        if (hoveredId !== undefined) {
          map.setFeatureState({ source: 'grid', id: hoveredId }, { hover: false });
          hoveredId = undefined;
        }
        map.getCanvas().style.cursor = '';
      });

      sourceReadyRef.current = true;
    },
    []
  );

  const updateOpacity = useCallback((map: maplibregl.Map, opacity: number) => {
    if (map.getLayer('grid-fill')) {
      map.setPaintProperty('grid-fill', 'fill-opacity', [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        Math.min(opacity + 0.15, 1),
        opacity,
      ]);
    }
  }, []);

  const setLayerVisibility = useCallback((map: maplibregl.Map, visible: boolean) => {
    ['grid-fill', 'grid-line'].forEach((id) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
      }
    });
  }, []);

  return { addGridSource, updateOpacity, setLayerVisibility, sourceReadyRef };
}
