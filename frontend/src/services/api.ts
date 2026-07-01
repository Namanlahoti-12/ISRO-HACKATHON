import { useQuery, useMutation } from '@tanstack/react-query';
import type { ConfigResponse, GridResponse, PixelDetail, ScenarioParams, SpatialPrediction, StatsEntry } from '../types/index';

const rawApiBase = (import.meta.env.VITE_API_URL ?? '').trim();
export const API_BASE = rawApiBase.replace(/\/+$/, '');
export const API = `${API_BASE}/api`;

export function apiUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${API}${suffix}`;
}

async function fetchJSON<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export function useConfig() {
  return useQuery<ConfigResponse>({
    queryKey: ['config'],
    queryFn: () => fetchJSON(apiUrl('/config')),
    staleTime: Infinity,
  });
}

export function useGridData() {
  return useQuery<GridResponse>({
    queryKey: ['grid'],
    queryFn: () => fetchJSON(apiUrl('/grid')),
    staleTime: 5 * 60_000,
  });
}

export function usePixelDetail(pixelId: number | null) {
  return useQuery<PixelDetail>({
    queryKey: ['pixel', pixelId],
    queryFn: () => fetchJSON(apiUrl(`/pixel/${pixelId}`)),
    enabled: pixelId !== null,
    staleTime: 60_000,
  });
}

export function useSpatialPredict() {
  return useMutation<SpatialPrediction, Error, ScenarioParams>({
    mutationFn: (params) =>
      fetchJSON(apiUrl('/predict/spatial'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      }),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => fetchJSON(apiUrl('/health')),
    staleTime: 30_000,
  });
}

export function useGridStats() {
  return useQuery<Record<string, StatsEntry>>({
    queryKey: ['grid_stats'],
    queryFn: () => fetchJSON(apiUrl('/grid_stats')),
    staleTime: Infinity,
  });
}
