import { useQuery, useMutation } from '@tanstack/react-query';
import type { ConfigResponse, GridResponse, PixelDetail, ScenarioParams, SpatialPrediction, StatsEntry } from '../types/index';

export const API_BASE = import.meta.env.VITE_API_URL || '';
const API = `${API_BASE}/api`;

async function fetchJSON<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

/* ── React Query Hooks ── */

export function useConfig() {
  return useQuery<ConfigResponse>({
    queryKey: ['config'],
    queryFn: () => fetchJSON(`${API}/config`),
    staleTime: Infinity,
  });
}

export function useGridData() {
  return useQuery<GridResponse>({
    queryKey: ['grid'],
    queryFn: () => fetchJSON(`${API}/grid`),
    staleTime: 5 * 60_000,
  });
}

export function usePixelDetail(pixelId: number | null) {
  return useQuery<PixelDetail>({
    queryKey: ['pixel', pixelId],
    queryFn: () => fetchJSON(`${API}/pixel/${pixelId}`),
    enabled: pixelId !== null,
    staleTime: 60_000,
  });
}

export function useSpatialPredict() {
  return useMutation<SpatialPrediction, Error, ScenarioParams>({
    mutationFn: (params) =>
      fetchJSON(`${API}/predict/spatial`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      }),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => fetchJSON(`${API}/health`),
    staleTime: 30_000,
  });
}

export function useGridStats() {
  return useQuery<Record<string, StatsEntry>>({
    queryKey: ['grid_stats'],
    queryFn: () => fetchJSON(`${API}/grid_stats`),
    staleTime: Infinity,   // stats don't change during a session
  });
}
