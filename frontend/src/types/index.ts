/* ── API Response Types ── */

export interface ConfigResponse {
  maps_api_key: string;
  center: { lat: number; lng: number };
  zoom: number;
  bounds: { north: number; south: number; east: number; west: number } | null;
  total_pixels: number;
  pixel_size_deg: number;
  model_name: string | null;
  n_features: number;
  hotspots: number;
  raster_ready?: boolean;
  raster_grid?: string | null;
  tile_url?: string | null;
}

export interface GridPixel {
  PixelID: number;
  Latitude: number;
  Longitude: number;
  HeatScore_Predicted: number;
  HeatClass_Predicted: number;
  HeatClass_Label: string;
  LST: number;
  NDVI: number;
  NDBI: number;
  NDWI: number;
  MNDWI: number;
  Population_Density: number;
  Building_Density: number;
  Building_Height: number;
  Road_Density_Proxy: number;
  Nighttime_Lights: number;
  WindSpeed: number;
  Humidity: number;
  SolarRadiation: number;
  UHI_Intensity: number;
  UTFVI: number;
  Albedo: number;
  Impervious_Frac: number;
  Tree_Cover_Pct: number;
  AirTemp: number;
  Elevation: number;
  Slope?: number;
  Anthropogenic_Heat: number;
  Dist_Water: number;
  Dist_Green: number;
  Green_Space_Density: number;
  UTCI_Approx: number;
  WindDirection: number;
  LULC_Derived?: number;
  [key: string]: string | number | undefined;
}

export interface StatsEntry {
  min: number;
  max: number;
  mean: number;
  std: number;
}

export interface GridResponse {
  columns: string[];
  pixels: GridPixel[];
  stats: Record<string, StatsEntry>;
}

export interface TopDriver {
  feature: string;
  contribution_pct: number;
  direction: 'heating' | 'cooling';
  value: number;
}

export interface PixelDetail {
  pixel_id: number;
  latitude: number;
  longitude: number;
  heat_score: number;
  lst: number;
  air_temp: number;
  heat_class: string;
  features: Record<string, number>;
  contributions: Record<string, number>;
  top_drivers: TopDriver[];
  recommendation: string;
  predicted_reduction: number;
  cost_estimate: number;
  priority: string;
  confidence: number;
}

export interface SpatialPixel { id: number; b: number; a: number; d: number; }

export interface SpatialPrediction {
  pixels: SpatialPixel[];
  summary: {
    before_mean: number;
    after_mean: number;
    reduction: number;
    reduction_pct: number;
  };
  timestamp?: number;
}

export interface ScenarioParams {
  tree_cover_pct: number;
  green_roof_pct: number;
  cool_roof_pct: number;
  water_body_pct: number;
  albedo_change: number;
  impervious_reduction_pct: number;
  building_density_reduction_pct: number;
}

/* ── Layer Definition ── */

export interface LayerDef {
  key: string;
  name: string;
  icon: string;
  unit: string;
  colors: string[];
  group?: string;
}

export type SimView = 'before' | 'after' | 'diff';
