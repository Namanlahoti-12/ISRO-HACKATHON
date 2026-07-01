import { useState, useCallback } from 'react';
import { useStore } from '../store/useStore';

interface GeocoderResult {
  lat: number;
  lng: number;
  display_name?: string;
}

export function useGeocoder() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<GeocoderResult[]>([]);
  const setFlyTo = useStore((s) => s.setFlyTo);

  const geocode = useCallback(async (query: string): Promise<GeocoderResult | null> => {
    if (!query.trim()) return null;

    // Check for lat,lng pattern first
    const m = query.trim().match(/^(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)$/);
    if (m) {
      const result = { lat: +m[1], lng: +m[2] };
      setFlyTo({ ...result, zoom: 16 });
      return result;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await res.json();
      if (data?.length) {
        const results: GeocoderResult[] = data.map((d: any) => ({
          lat: +d.lat,
          lng: +d.lon,
          display_name: d.display_name,
        }));
        setSuggestions(results);
        return results[0];
      }
      setError('No results found');
      return null;
    } catch {
      setError('Geocoding failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, [setFlyTo]);

  const flyToResult = useCallback((result: GeocoderResult) => {
    setFlyTo({ lat: result.lat, lng: result.lng, zoom: 14 });
    setSuggestions([]);
    
    // Trigger backend GEE pipeline processing for the new AOI
    fetch('/api/search_aoi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat: result.lat, lng: result.lng }),
    }).then(res => res.json()).then(data => {
      console.log('[GEE Pipeline]', data.message);
      if (data.success) {
        // In a real app, this would trigger a map data reload after a few minutes
      }
    }).catch(err => {
      console.error('[GEE Pipeline] Error:', err);
    });

  }, [setFlyTo]);

  const clearSuggestions = useCallback(() => setSuggestions([]), []);

  return { geocode, flyToResult, loading, error, suggestions, clearSuggestions };
}
