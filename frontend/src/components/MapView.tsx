/**
 * MapView — Raster Tile Rendering (GEE-style)
 * ─────────────────────────────────────────────
 * Data flow:
 *   GEE GeoTIFFs → AI model → predicted rasters → XYZ tile server
 *   Frontend: Adds MapLibre raster source per layer, swaps on sidebar click
 *
 * Each sidebar layer gets its own raster tile source:
 *   /api/tiles/{layer_key}/{z}/{x}/{y}.png
 * Tiles are pre-coloured server-side with the correct colour ramp.
 */

import { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { useStore } from '../store/useStore';
import { useConfig, useGridStats, apiUrl } from '../services/api';
import { DARK_STYLE, OSM_FALLBACK, DARK_STYLE_URL, LIGHT_STYLE_URL } from '../maps/layerConfig';

// ── Constants ───────────────────────────────────────────────────────────────
const RASTER_SRC_PREFIX = 'raster-src-';
const RASTER_LYR_PREFIX = 'raster-lyr-';

/** Build tile URL for a layer */
const tileUrl = (layerKey: string) =>
  apiUrl(`/tiles/${layerKey}/{z}/{x}/{y}.png`);

export function MapView() {
  const containerRef    = useRef<HTMLDivElement>(null);
  const mapRef          = useRef<maplibregl.Map | null>(null);
  const mapLoadedRef    = useRef(false);
  const pendingRef      = useRef<(() => void) | null>(null);
  const popupRef        = useRef<maplibregl.Popup | null>(null);
  const markerRef       = useRef<maplibregl.Marker | null>(null);
  const currentLayerRef = useRef<string>('');

  const { data: config }     = useConfig();
  const { data: gridStats }  = useGridStats();

  const darkMode         = useStore((s) => s.darkMode);
  const activeLayer      = useStore((s) => s.activeLayer);
  const opacity          = useStore((s) => s.opacity);
  const flyToTarget      = useStore((s) => s.flyToTarget);
  const hiddenLayers     = useStore((s) => s.hiddenLayers);
  const setCursorCoords  = useStore((s) => s.setCursorCoords);
  const setMapReady      = useStore((s) => s.setMapReady);
  const setFlyTo         = useStore((s) => s.setFlyTo);
  const simView          = useStore((s) => s.simView);
  const spatialResult    = useStore((s) => s.spatialResult);

  /* ─── Determine active raster layer name based on simulation ─── */
  const getSimulatedLayerKey = useCallback((baseLayer: string, view: string) => {
    if (baseLayer === 'HeatScore_Predicted') {
      if (view === 'after') return 'HeatScore_Predicted_simulated';
      if (view === 'diff') return 'HeatScore_Predicted_diff';
    }
    return baseLayer;
  }, []);

  /* ─── Add a raster tile layer for a given key ─── */
  const addRasterLayer = useCallback(
    (map: maplibregl.Map, layerKey: string, opacityVal: number, visible: boolean, ts: number = 0) => {
      const srcId = RASTER_SRC_PREFIX + layerKey;
      const lyrId = RASTER_LYR_PREFIX + layerKey;

      if (map.getSource(srcId)) {
        // MapLibre doesn't support changing tile URL easily, so we just remove and re-add if timestamp changed
        // But since we only have one timestamp, we can just let switchLayer remove it if needed.
        return; 
      }

      const url = tileUrl(layerKey) + (ts ? `?t=${ts}` : '');

      map.addSource(srcId, {
        type: 'raster',
        tiles: [url],
        tileSize: 256,
        attribution: 'AI Prediction | ISRO Hackathon',
      });

      map.addLayer({
        id: lyrId,
        type: 'raster',
        source: srcId,
        paint: {
          'raster-opacity': opacityVal,
          'raster-fade-duration': 200,
        },
        layout: {
          visibility: visible ? 'visible' : 'none',
        },
      });
    },
    [],
  );

  /* ─── Remove a raster tile layer ─── */
  const removeRasterLayer = useCallback((map: maplibregl.Map, layerKey: string) => {
    const lyrId = RASTER_LYR_PREFIX + layerKey;
    const srcId = RASTER_SRC_PREFIX + layerKey;
    if (map.getLayer(lyrId)) map.removeLayer(lyrId);
    if (map.getSource(srcId)) map.removeSource(srcId);
  }, []);

  /* ─── Switch active raster layer ─── */
  const switchLayer = useCallback(
    (map: maplibregl.Map, newBaseLayer: string, opacityVal: number, view: string, ts: number = 0) => {
      const newLayer = getSimulatedLayerKey(newBaseLayer, view);
      const prevLayer = currentLayerRef.current;

      // Hide previous layer
      if (prevLayer && prevLayer !== newLayer) {
        const prevLyrId = RASTER_LYR_PREFIX + prevLayer;
        if (map.getLayer(prevLyrId)) {
          map.setLayoutProperty(prevLyrId, 'visibility', 'none');
        }
      }

      // If timestamp changed, force remove old simulated layer to reload tiles
      if (ts && (newLayer === 'HeatScore_Predicted_simulated' || newLayer === 'HeatScore_Predicted_diff')) {
        removeRasterLayer(map, newLayer);
      }

      // Add new layer if needed, then show it
      addRasterLayer(map, newLayer, opacityVal, true, ts);
      const newLyrId = RASTER_LYR_PREFIX + newLayer;
      if (map.getLayer(newLyrId)) {
        map.setLayoutProperty(newLyrId, 'visibility', 'visible');
        map.setPaintProperty(newLyrId, 'raster-opacity', opacityVal);
      }

      currentLayerRef.current = newLayer;
    },
    [addRasterLayer, getSimulatedLayerKey, removeRasterLayer],
  );

  /* ─── Click handler for pixel info popup ─── */
  const handleMapClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      if (popupRef.current) popupRef.current.remove();

      const { lat, lng } = e.lngLat;

      // Fetch pixel info from the grid API
      fetch(apiUrl('/grid'))
        .then((r) => r.json())
        .then((data) => {
          if (!data.pixels?.length) return;

          // Find nearest pixel to click location
          let minDist = Infinity;
          let nearest: Record<string, unknown> | null = null;
          for (const px of data.pixels) {
            const d = Math.hypot(
              (px.Latitude as number) - lat,
              (px.Longitude as number) - lng,
            );
            if (d < minDist) {
              minDist = d;
              nearest = px;
            }
          }

          if (!nearest || minDist > 0.02) return; // too far

          const p = nearest;
          popupRef.current = new maplibregl.Popup({
            closeButton: true,
            maxWidth: '300px',
            className: 'heat-popup',
            offset: 12,
          })
            .setLngLat(e.lngLat)
            .setHTML(`
              <div class="popup-inner">
                <div class="popup-score">Heat Score: ${Number(p.HeatScore_Predicted ?? 0).toFixed(1)}</div>
                <div class="popup-class">${p.HeatClass_Label ?? ''}</div>
                <div class="popup-coords">${lat.toFixed(4)}N, ${lng.toFixed(4)}E</div>
                <div class="popup-stats">
                  <span>LST: ${Number(p.LST ?? 0).toFixed(1)} C</span>
                  <span>NDVI: ${Number(p.NDVI ?? 0).toFixed(3)}</span>
                  <span>NDBI: ${Number(p.NDBI ?? 0).toFixed(3)}</span>
                  <span>Pop: ${Number(p.Population_Density ?? 0).toFixed(1)}</span>
                  <span>Bld: ${Number(p.Building_Density ?? 0).toFixed(2)}</span>
                  <span>Humidity: ${Number(p.Humidity ?? 0).toFixed(0)}%</span>
                  <span>Wind: ${Number(p.WindSpeed ?? 0).toFixed(1)} m/s</span>
                  <span>UHI: ${Number(p.UHI_Intensity ?? 0).toFixed(2)} C</span>
                  <span>Albedo: ${Number(p.Albedo ?? 0).toFixed(3)}</span>
                  <span>Elev: ${Number(p.Elevation ?? 0).toFixed(0)} m</span>
                </div>
              </div>
            `)
            .addTo(mapRef.current!);
        })
        .catch(() => {});
    },
    [],
  );

  /* ─── INIT MAP ─── */
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const primaryStyle = darkMode ? DARK_STYLE : OSM_FALLBACK;

    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container:             containerRef.current,
        style:                 primaryStyle,
        center:                [config?.center.lng ?? 77.209, config?.center.lat ?? 28.614],
        zoom:                  config?.zoom ?? 12,
        attributionControl:    { compact: true },
        maxPitch:              60,
        preserveDrawingBuffer: true,
        antialias:             true,
      });
    } catch (err) {
      console.error('[MapView] Init failed:', err);
      return;
    }

    (window as any).__mapRef = map;

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 140, unit: 'metric' }), 'bottom-left');
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');
    map.addControl(
      new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }),
      'top-right',
    );

    map.on('mousemove', (e) =>
      setCursorCoords({ lat: +e.lngLat.lat.toFixed(5), lng: +e.lngLat.lng.toFixed(5) }),
    );
    map.on('mouseleave', () => setCursorCoords(null));
    map.on('click', handleMapClick);

    const onMapReady = () => {
      if (mapLoadedRef.current) return;
      mapRef.current       = map;
      mapLoadedRef.current = true;
      (window as any).__mapInstance = map;
      setMapReady(true);

      if (config?.bounds) {
        map.fitBounds(
          [[config.bounds.west, config.bounds.south], [config.bounds.east, config.bounds.north]],
          { padding: 60, maxZoom: 14, duration: 1500 },
        );
      }

      // Add the default raster layer
      const startLayer = (window as any).__activeLayer ?? 'HeatScore_Predicted';
      const startOpacity = (window as any).__opacity ?? 0.7;
      addRasterLayer(map, startLayer, startOpacity, true);
      currentLayerRef.current = startLayer;

      if (pendingRef.current) { pendingRef.current(); pendingRef.current = null; }
    };

    map.on('load',      onMapReady);
    map.on('styledata', () => { if (!mapLoadedRef.current && map.isStyleLoaded()) onMapReady(); });
    map.on('idle',      () => { if (!mapLoadedRef.current) onMapReady(); });

    const forceTimer = setTimeout(() => { if (!mapLoadedRef.current) onMapReady(); }, 4000);

    // Async upgrade to OpenFreeMap vector basemap
    setTimeout(async () => {
      if (!mapLoadedRef.current) return;
      const vectorUrl = darkMode ? DARK_STYLE_URL : LIGHT_STYLE_URL;
      try {
        const res = await fetch(vectorUrl, { signal: AbortSignal.timeout(5000) });
        if (!res.ok) return;
        map.once('style.load', () => {
          const al = (window as any).__activeLayer ?? 'HeatScore_Predicted';
          const op = (window as any).__opacity ?? 0.7;
          addRasterLayer(map, al, op, true);
          currentLayerRef.current = al;
        });
        map.setStyle(vectorUrl);
      } catch { /* keep CARTO */ }
    }, 3500);

    return () => {
      clearTimeout(forceTimer);
      map.remove();
      mapRef.current       = null;
      mapLoadedRef.current = false;
      (window as any).__mapInstance = undefined;
      (window as any).__mapRef      = undefined;
      setMapReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Keep window refs current */
  useEffect(() => { (window as any).__activeLayer = activeLayer; }, [activeLayer]);
  useEffect(() => { (window as any).__opacity     = opacity;     }, [opacity]);

  /* ─── Switch raster layer when sidebar selection or simulation changes ─── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoadedRef.current) return;
    switchLayer(map, activeLayer, opacity, simView, spatialResult?.timestamp ?? 0);
  }, [activeLayer, opacity, simView, spatialResult, switchLayer]);

  /* ─── Eye-icon visibility toggle ─── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoadedRef.current) return;
    const lyrId = RASTER_LYR_PREFIX + activeLayer;
    if (map.getLayer(lyrId)) {
      const vis = hiddenLayers.has(activeLayer) ? 'none' : 'visible';
      map.setLayoutProperty(lyrId, 'visibility', vis);
    }
  }, [hiddenLayers, activeLayer]);

  /* ─── Dark/Light theme switch ─── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoadedRef.current) return;
    map.once('style.load', () => {
      const al = activeLayer;
      const op = opacity;
      addRasterLayer(map, al, op, true);
      currentLayerRef.current = al;
    });
    map.setStyle(darkMode ? DARK_STYLE : OSM_FALLBACK);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [darkMode]);

  /* ─── Fly-to from search ─── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyToTarget) return;
    map.flyTo({ center: [flyToTarget.lng, flyToTarget.lat], zoom: flyToTarget.zoom ?? 14, duration: 2200, essential: true });
    if (markerRef.current) markerRef.current.remove();
    markerRef.current = new maplibregl.Marker({ color: '#06b6d4' })
      .setLngLat([flyToTarget.lng, flyToTarget.lat])
      .addTo(map);
    setFlyTo(null);
  }, [flyToTarget, setFlyTo]);

  return <div ref={containerRef} className="map-container" />;
}
