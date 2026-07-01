// ============================================================================
// MODULE: config.js — Central Configuration
// ============================================================================
// All user-configurable parameters for the Urban Heat AI pipeline.
// This module is referenced by every other module.
// In the runnable main.js, these values appear at the top of the script.
// ============================================================================

// ─── City Selection ─────────────────────────────────────────────────────────
var CITY_NAME       = 'Delhi';
var CENTER_LAT      = 28.6139;
var CENTER_LON      = 77.2090;
var BUFFER_RADIUS_M = 25000;         // 25 km radius

// ─── Administrative Boundary (alternative to lat/lon) ───────────────────────
var USE_ADMIN_BOUNDARY   = false;
var ADMIN_DISTRICT_NAME  = 'Delhi';

// ─── Date Range ─────────────────────────────────────────────────────────────
// For UHI studies in India, target pre-monsoon summer (March–June).
var START_DATE = '2024-03-01';
var END_DATE   = '2024-06-30';

// ─── Cloud Cover ────────────────────────────────────────────────────────────
var MAX_CLOUD_PERCENT = 20;          // % maximum scene-level cloud cover

// ─── Export Settings ────────────────────────────────────────────────────────
var EXPORT_SCALE     = 30;           // Pixel resolution in meters
var EXPORT_CRS       = 'EPSG:4326'; // WGS84 geographic coordinates
var DRIVE_FOLDER     = 'ISRO_UHI_Data';
var MAX_PIXELS       = 1e13;

// ─── CSV Sampling ───────────────────────────────────────────────────────────
var CSV_SAMPLE_SCALE = 100;          // Spacing between sample points (meters)
var MAX_CSV_POINTS   = 100000;       // Maximum rows in CSV
var RANDOM_SEED      = 42;           // For reproducibility

// ─── Neighborhood Analysis ──────────────────────────────────────────────────
// Kernel radius for spatial density/roughness features (in pixels).
var KERNEL_RADIUS    = 5;            // 5 pixels × 30m = 150m neighborhood

// ─── LST Emissivity Thresholds (Sobrino et al., 2004) ───────────────────────
var NDVI_SOIL   = 0.2;              // NDVI threshold for bare soil
var NDVI_VEG    = 0.5;              // NDVI threshold for full vegetation
var EMISS_SOIL  = 0.996;            // Emissivity of bare soil
var EMISS_VEG   = 0.973;            // Emissivity of vegetation

// ─── GEE Collection IDs ─────────────────────────────────────────────────────
// Centralized dataset references for easy maintenance.
var COLLECTIONS = {
  LANDSAT8:       'LANDSAT/LC08/C02/T1_L2',
  LANDSAT9:       'LANDSAT/LC09/C02/T1_L2',
  SENTINEL2:      'COPERNICUS/S2_SR_HARMONIZED',
  S2_CLOUD_PROB:  'COPERNICUS/S2_CLOUD_PROBABILITY',
  ERA5_LAND:      'ECMWF/ERA5_LAND/HOURLY',
  ERA5_DAILY:     'ECMWF/ERA5/DAILY',
  WORLDCOVER:     'ESA/WorldCover/v200',
  DYNAMIC_WORLD:  'GOOGLE/DYNAMICWORLD/V1',
  GHSL_BUILT_S:   'JRC/GHSL/P2023A/GHS_BUILT_S',
  GHSL_BUILT_H:   'JRC/GHSL/P2023A/GHS_BUILT_H',
  GHSL_POP:       'JRC/GHSL/P2023A/GHS_POP',
  WORLDPOP:       'WorldPop/GP/100m/pop',
  SRTM:           'USGS/SRTMGL1_003',
  VIIRS:          'NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG',
  GAIA:           'Tsinghua/FROM-GLC/GAIA/v10',
  HANSEN:         'UMD/hansen/global_forest_change_2023_v1_11',
  GAUL:           'FAO/GAUL/2015/level2'
};

// ─── Visualization Palettes ─────────────────────────────────────────────────
var PALETTES = {
  LST: ['1a3678','2955bc','5699ff','8dbae9','acd1ff','caebf2',
        'e0f3db','a8ddb5','7bccc4','f7fcb9','fff7bc','fec44f',
        'fe9929','ec7014','cc4c02','993404','662506'],
  NDVI: ['d73027','f46d43','fdae61','fee08b','d9ef8b','a6d96a',
         '66bd63','1a9850','006837'],
  NDBI: ['2166ac','67a9cf','d1e5f0','fddbc7','ef8a62','b2182b'],
  NDWI: ['d73027','fc8d59','fee090','e0f3f8','91bfdb','4575b4'],
  TEMP: ['blue','cyan','yellow','orange','red'],
  HUMIDITY: ['ffffcc','a1dab4','41b6c4','225ea8'],
  WIND: ['ffffff','c6dbef','6baed6','2171b5','08306b'],
  SOLAR: ['f7fcf5','d9f0a3','addd8e','78c679','31a354','006837'],
  ELEVATION: ['006837','1a9850','66bd63','a6d96a','d9ef8b',
              'fee08b','fdae61','f46d43','d73027'],
  NIGHTLIGHTS: ['000000','1a1a2e','16213e','0f3460',
                '533483','e94560','f38181','fce38a','eaffd0'],
  POPULATION: ['ffffcc','ffeda0','fed976','feb24c','fd8d3c',
               'fc4e2a','e31a1c','bd0026','800026'],
  UHI: ['313695','4575b4','74add1','abd9e9','e0f3f8',
        'ffffbf','fee090','fdae61','f46d43','d73027','a50026']
};
