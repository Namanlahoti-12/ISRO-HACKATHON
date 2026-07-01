import { create } from 'zustand';
import type { ScenarioParams, SimView, SpatialPrediction } from '../types';

const DEFAULT_SCENARIO: ScenarioParams = {
  tree_cover_pct: 0, green_roof_pct: 0, cool_roof_pct: 0,
  water_body_pct: 0, albedo_change: 0, impervious_reduction_pct: 0,
  building_density_reduction_pct: 0,
};

interface AppState {
  darkMode: boolean;
  toggleDarkMode: () => void;

  activeLayer: string;
  setActiveLayer: (l: string) => void;

  opacity: number;
  setOpacity: (v: number) => void;

  selectedPixelId: number | null;
  setSelectedPixelId: (id: number | null) => void;

  detailOpen: boolean;
  setDetailOpen: (o: boolean) => void;

  sidebarOpen: boolean;
  setSidebarOpen: (o: boolean) => void;

  simExpanded: boolean;
  setSimExpanded: (e: boolean) => void;

  simView: SimView;
  setSimView: (v: SimView) => void;

  scenario: ScenarioParams;
  setScenarioParam: (key: keyof ScenarioParams, val: number) => void;
  resetScenario: () => void;

  spatialResult: SpatialPrediction | null;
  setSpatialResult: (r: SpatialPrediction | null) => void;

  hiddenLayers: Set<string>;
  toggleHiddenLayer: (key: string) => void;

  cursorCoords: { lat: number; lng: number } | null;
  setCursorCoords: (c: { lat: number; lng: number } | null) => void;

  mapReady: boolean;
  setMapReady: (r: boolean) => void;

  flyToTarget: { lat: number; lng: number; zoom?: number } | null;
  setFlyTo: (t: { lat: number; lng: number; zoom?: number } | null) => void;

  gridView: boolean;
  toggleGridView: () => void;
}

export const useStore = create<AppState>((set) => ({
  darkMode: true,
  toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),

  activeLayer: 'HeatScore_Predicted',
  setActiveLayer: (l) => set({ activeLayer: l }),

  opacity: 0.35,
  setOpacity: (v) => set({ opacity: v }),

  selectedPixelId: null,
  setSelectedPixelId: (id) => set({ selectedPixelId: id }),

  detailOpen: false,
  setDetailOpen: (o) => set({ detailOpen: o }),

  sidebarOpen: true,
  setSidebarOpen: (o) => set({ sidebarOpen: o }),

  simExpanded: false,
  setSimExpanded: (e) => set({ simExpanded: e }),

  simView: 'before',
  setSimView: (v) => set({ simView: v }),

  scenario: { ...DEFAULT_SCENARIO },
  setScenarioParam: (key, val) => set((s) => ({
    scenario: { ...s.scenario, [key]: val },
  })),
  resetScenario: () => set({
    scenario: { ...DEFAULT_SCENARIO },
    spatialResult: null,
    simView: 'before',
  }),

  spatialResult: null,
  setSpatialResult: (r) => set({ spatialResult: r }),

  hiddenLayers: new Set<string>(),
  toggleHiddenLayer: (key) => set((s) => {
    const next = new Set(s.hiddenLayers);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return { hiddenLayers: next };
  }),

  cursorCoords: null,
  setCursorCoords: (c) => set({ cursorCoords: c }),

  mapReady: false,
  setMapReady: (r) => set({ mapReady: r }),

  flyToTarget: null,
  setFlyTo: (t) => set({ flyToTarget: t }),

  gridView: false,
  toggleGridView: () => set((s) => ({ gridView: !s.gridView })),
}));
