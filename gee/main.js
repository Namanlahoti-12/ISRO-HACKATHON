// ╔═══════════════════════════════════════════════════════════════════════════════╗
// ║                                                                               ║
// ║   URBAN HEAT AI — PRODUCTION DATA PIPELINE v2.0                               ║
// ║   ISRO Bharatiya Antariksh Hackathon                                          ║
// ║                                                                               ║
// ║   Complete Google Earth Engine script for Urban Heat Island analysis.          ║
// ║   Collects 40+ features from 15+ datasets. Exports AI-ready CSV.             ║
// ║                                                                               ║
// ║   HOW TO USE:                                                                 ║
// ║     1. Open https://code.earthengine.google.com                               ║
// ║     2. Create a new script (File → New)                                       ║
// ║     3. Paste this ENTIRE file                                                 ║
// ║     4. Edit SECTION 1 (Configuration) for your target city                    ║
// ║     5. Click "Run"                                                            ║
// ║     6. Go to "Tasks" tab → click "Run" on each export task                   ║
// ║                                                                               ║
// ╚═══════════════════════════════════════════════════════════════════════════════╝


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 1: CONFIGURATION                                                   █
// █  Change these values for your target city. Everything else is automatic.     █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 1a. City Selection ─────────────────────────────────────────────────────
// Option A: Latitude/Longitude with buffer radius.
// Find coordinates from Google Maps: right-click any point → copy coordinates.
var CITY_NAME       = 'Delhi';       // Used in export file names
var CENTER_LAT      = 28.6139;       // Latitude of city center
var CENTER_LON      = 77.2090;       // Longitude of city center
var BUFFER_RADIUS_M = 25000;         // Buffer in meters (25 km)

// Option B: Administrative boundary from FAO GAUL.
// Set USE_ADMIN_BOUNDARY = true to use district boundary instead of buffer.
var USE_ADMIN_BOUNDARY   = false;
var ADMIN_DISTRICT_NAME  = 'Delhi';  // District name in GAUL dataset

// ─── 1b. Date Range ─────────────────────────────────────────────────────────
// For UHI in India, use pre-monsoon summer: March–June.
var START_DATE = '2024-03-01';
var END_DATE   = '2024-06-30';

// ─── 1c. Cloud Cover Threshold ──────────────────────────────────────────────
// Maximum scene-level cloud cover percentage (lower = cleaner but fewer images).
var MAX_CLOUD_PERCENT = 20;

// ─── 1d. Export Settings ────────────────────────────────────────────────────
var EXPORT_SCALE = 30;               // Pixel size in meters (30m = Landsat native)
var DRIVE_FOLDER = 'ISRO_UHI_Data';  // Google Drive folder for exports

// ─── 1e. CSV Sampling ───────────────────────────────────────────────────────
var CSV_SAMPLE_SCALE = 100;          // Spacing between CSV sample points (meters)
var MAX_CSV_POINTS   = 100000;       // Maximum rows in output CSV

// ─── 1f. Neighborhood Analysis ──────────────────────────────────────────────
// Kernel radius in pixels for spatial density features (5 px × 30m = 150m).
var KERNEL_RADIUS = 5;

// ─── 1g. Population Year ────────────────────────────────────────────────────
var POP_YEAR = 2020;                 // Year for WorldPop data


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 2: STUDY AREA DEFINITION                                            █
// ████████████████████████████████████████████████████████████████████████████████

// Create a point from lat/lon. Note: ee.Geometry.Point takes [lon, lat].
var cityCenter = ee.Geometry.Point([CENTER_LON, CENTER_LAT]);

var studyArea;
if (USE_ADMIN_BOUNDARY) {
  // Look up administrative boundary from FAO GAUL Level 2 dataset.
  var gaul = ee.FeatureCollection('FAO/GAUL/2015/level2');
  var district = gaul
    .filter(ee.Filter.eq('ADM0_NAME', 'India'))
    .filter(ee.Filter.eq('ADM2_NAME', ADMIN_DISTRICT_NAME));
  studyArea = district.geometry();
  print('✓ Admin boundary loaded:', ADMIN_DISTRICT_NAME);
} else {
  // Create circular buffer around city center.
  studyArea = cityCenter.buffer(BUFFER_RADIUS_M);
  print('✓ Study area: ' + BUFFER_RADIUS_M/1000 + ' km buffer around ' + CITY_NAME);
}

// Center map on study area.
Map.centerObject(studyArea, 11);

// Draw boundary outline (yellow).
Map.addLayer(
  ee.Image().paint(ee.FeatureCollection([ee.Feature(studyArea)]), 0, 2),
  {palette: ['FFD700']}, 'Study Area Boundary'
);

print('Study area size (sq km):', studyArea.area().divide(1e6));


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 3: CLOUD MASKING & SCALING FUNCTIONS                                █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 3a. Landsat-8/9 Cloud Mask ─────────────────────────────────────────────
// QA_PIXEL bits: 1=Dilated Cloud, 2=Cirrus, 3=Cloud Shadow, 4=Cloud
function maskLandsatClouds(image) {
  var qa = image.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(1 << 1).eq(0)   // No dilated cloud
    .and(qa.bitwiseAnd(1 << 2).eq(0))      // No cirrus
    .and(qa.bitwiseAnd(1 << 3).eq(0))      // No cloud shadow
    .and(qa.bitwiseAnd(1 << 4).eq(0));     // No cloud
  // Also remove saturated pixels.
  var satMask = image.select('QA_RADSAT').eq(0);
  return image.updateMask(mask).updateMask(satMask);
}

// ─── 3b. Landsat Scaling (Collection 2 Level 2) ────────────────────────────
// Surface Reflectance: val × 0.0000275 + (−0.2), clamped to [0, 1].
// Surface Temperature: val × 0.00341802 + 149.0 → Kelvin.
function scaleLandsat(image) {
  var optical = image.select('SR_B.*')
    .multiply(0.0000275).add(-0.2).clamp(0, 1);
  var thermal = image.select('ST_B10')
    .multiply(0.00341802).add(149.0);
  return image.addBands(optical, null, true)
              .addBands(thermal, null, true);
}

// ─── 3c. Sentinel-2 Cloud Mask ──────────────────────────────────────────────
// QA60 bits: 10=Opaque Cloud, 11=Cirrus
function maskS2Clouds(image) {
  var qa = image.select('QA60');
  var mask = qa.bitwiseAnd(1 << 10).eq(0)
    .and(qa.bitwiseAnd(1 << 11).eq(0));
  return image.updateMask(mask);
}

// ─── 3d. Sentinel-2 Scaling ────────────────────────────────────────────────
// SR bands stored as integers × 10000. Divide to get reflectance [0, 1].
function scaleS2(image) {
  var bands = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'];
  var scaled = image.select(bands).divide(10000).clamp(0, 1);
  return image.addBands(scaled, null, true);
}


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 4: LANDSAT-8 & LANDSAT-9 PROCESSING                                █
// ████████████████████████████████████████████████████████████████████████████████
// Landsat-8 and Landsat-9 have identical band structures.
// Merging both doubles the number of available scenes for compositing.

// Load Landsat-8 Collection 2 Level 2.
var landsat8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE)
  .filter(ee.Filter.lt('CLOUD_COVER', MAX_CLOUD_PERCENT));

// Load Landsat-9 Collection 2 Level 2 (launched Oct 2021).
var landsat9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE)
  .filter(ee.Filter.lt('CLOUD_COVER', MAX_CLOUD_PERCENT));

print('Landsat-8 images found:', landsat8.size());
print('Landsat-9 images found:', landsat9.size());

// Merge both collections, apply scaling and cloud masking.
var landsatMerged = landsat8.merge(landsat9)
  .map(scaleLandsat)
  .map(maskLandsatClouds);

// Create median composite — pixel-wise median removes remaining outliers.
var landsatComposite = landsatMerged.median().clip(studyArea);

// Count valid observations per pixel (quality score).
var landsatCount = landsatMerged.select('SR_B4').count()
  .clip(studyArea).rename('QualityScore');

print('✓ Landsat-8/9 composite created (merged ' +
  'L8 + L9, cloud-masked, median).');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 5: SENTINEL-2 PROCESSING                                           █
// ████████████████████████████████████████████████████████████████████████████████
// Sentinel-2 provides 10m optical imagery for higher-resolution indices.

var sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD_PERCENT))
  .map(scaleS2)
  .map(maskS2Clouds);

print('Sentinel-2 images found:', sentinel2.size());

var s2Composite = sentinel2.median().clip(studyArea);
print('✓ Sentinel-2 composite created.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 6: SPECTRAL INDICES                                                 █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 6a. NDVI — Vegetation Index ────────────────────────────────────────────
// Formula: (NIR − Red) / (NIR + Red) | Landsat: B5, B4
// Positive → vegetation; Higher → denser/healthier greenery.
var ndvi = landsatComposite.normalizedDifference(['SR_B5', 'SR_B4'])
  .rename('NDVI');

// ─── 6b. NDBI — Built-up Index ─────────────────────────────────────────────
// Formula: (SWIR1 − NIR) / (SWIR1 + NIR) | Landsat: B6, B5
// Positive → built-up surfaces (concrete, asphalt).
var ndbi = landsatComposite.normalizedDifference(['SR_B6', 'SR_B5'])
  .rename('NDBI');

// ─── 6c. NDWI — Water Index ────────────────────────────────────────────────
// Formula: (Green − NIR) / (Green + NIR) | Landsat: B3, B5
// Positive → open water bodies.
var ndwi = landsatComposite.normalizedDifference(['SR_B3', 'SR_B5'])
  .rename('NDWI');

// ─── 6d. MNDWI — Modified Water Index ──────────────────────────────────────
// Formula: (Green − SWIR1) / (Green + SWIR1) | Landsat: B3, B6
// Better than NDWI in urban areas (SWIR suppresses built-up noise).
var mndwi = landsatComposite.normalizedDifference(['SR_B3', 'SR_B6'])
  .rename('MNDWI');

// ─── 6e. SAVI — Soil Adjusted Vegetation Index ─────────────────────────────
// SAVI = ((NIR − Red) / (NIR + Red + L)) × (1 + L), where L = 0.5
// More accurate than NDVI in areas with sparse vegetation and exposed soil.
// Reference: Huete (1988)
var nir = landsatComposite.select('SR_B5');
var red = landsatComposite.select('SR_B4');
var L = 0.5;  // Soil brightness correction factor
var savi = nir.subtract(red).divide(nir.add(red).add(L)).multiply(1 + L)
  .rename('SAVI');

// ─── 6f. Shortwave Surface Albedo (Liang 2001) ─────────────────────────────
// α = 0.356×B2 + 0.130×B4 + 0.373×B5 + 0.085×B6 + 0.072×B7 − 0.0018
// Low albedo → absorbs more solar energy → heats up more.
var albedo = landsatComposite.select('SR_B2').multiply(0.356)
  .add(landsatComposite.select('SR_B4').multiply(0.130))
  .add(landsatComposite.select('SR_B5').multiply(0.373))
  .add(landsatComposite.select('SR_B6').multiply(0.085))
  .add(landsatComposite.select('SR_B7').multiply(0.072))
  .subtract(0.0018)
  .clamp(0, 1)
  .rename('Albedo');

// ─── 6f. Sentinel-2 NDVI (10m) ─────────────────────────────────────────────
// Higher resolution vegetation map.
var ndviS2 = s2Composite.normalizedDifference(['B8', 'B4'])
  .rename('NDVI_S2');

print('✓ Spectral indices computed: NDVI, NDBI, NDWI, MNDWI, Albedo, NDVI_S2.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 7: LAND SURFACE TEMPERATURE (LST)                                   █
// ████████████████████████████████████████████████████████████████████████████████
// ST_B10 from Landsat C2 L2 is already atmospherically and emissivity-corrected
// using the USGS single-channel algorithm with ASTER GED emissivity.
// Convert Kelvin → Celsius, clamp to valid range.

var lst = landsatComposite.select('ST_B10')
  .subtract(273.15)                  // K → °C
  .clamp(-10, 70)                    // Valid range for Indian cities
  .rename('LST');

print('LST range (°C):', lst.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: studyArea, scale: 30, maxPixels: 1e9
}));

// ─── UHI Intensity ──────────────────────────────────────────────────────────
// UHII = LST_pixel − mean LST of non-urban (rural) pixels.
// "Rural" = all pixels where ESA WorldCover ≠ 50 (Built-up).
// We load WorldCover here early because UHII needs it.
var worldCover = ee.ImageCollection('ESA/WorldCover/v200')
  .first().clip(studyArea);

var ruralMask = worldCover.neq(50);  // Everything except built-up
var ruralLST  = lst.updateMask(ruralMask);
var ruralMeanDict = ruralLST.reduceRegion({
  reducer: ee.Reducer.mean(),
  geometry: studyArea, scale: 100, maxPixels: 1e9
});
var ruralMeanLST = ee.Number(ruralMeanDict.get('LST'));
var uhiIntensity = lst.subtract(ruralMeanLST).rename('UHI_Intensity');

print('Rural mean LST (°C):', ruralMeanLST);

// ─── UTFVI (Urban Thermal Field Variance Index) ────────────────────────────
// UTFVI = (LST − LST_mean) / LST_mean
// Classifies ecological quality: <0=Excellent, 0–0.005=Good, etc.
var lstMeanDict = lst.reduceRegion({
  reducer: ee.Reducer.mean(),
  geometry: studyArea, scale: 100, maxPixels: 1e9
});
var lstMean = ee.Number(lstMeanDict.get('LST'));
var utfvi = lst.subtract(lstMean).divide(lstMean).rename('UTFVI');

print('✓ LST, UHI Intensity, UTFVI computed.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 8: LAND USE / LAND COVER (LULC)                                     █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 8a. ESA WorldCover (10m, 2021) ─────────────────────────────────────────
// Primary LULC. Classes: 10=Trees, 20=Shrub, 30=Grass, 40=Crop,
// 50=Built-up, 60=Bare, 70=Snow, 80=Water, 90=Wetland, 95=Mangroves, 100=Moss
var lulcESA = worldCover.rename('LULC_ESA');

// ─── 8b. Google Dynamic World (10m, near real-time) ─────────────────────────
// ML-based LULC with per-pixel class probabilities.
// Classes: 0=Water, 1=Trees, 2=Grass, 3=Flooded Veg, 4=Crops,
// 5=Shrub/Scrub, 6=Built, 7=Bare, 8=Snow/Ice
var dynamicWorld = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE)
  .select('label');
var lulcDW = dynamicWorld.reduce(ee.Reducer.mode())
  .clip(studyArea)
  .rename('LULC_DW');

// ─── 8c. GAIA Impervious Surface (30m) ──────────────────────────────────────
// Binary impervious surface mapping (Tsinghua University).
// change_year_index > 0 means the pixel was mapped as impervious.
var gaiaRaw = ee.Image('Tsinghua/FROM-GLC/GAIA/v10');
var impervious = gaiaRaw.select('change_year_index')
  .gt(0)                             // 1 = impervious, 0 = not
  .clip(studyArea)
  .rename('Impervious_Frac');

// ─── 8d. Hansen Tree Cover (30m) ────────────────────────────────────────────
// Tree canopy cover percentage in year 2000.
var treeCover = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
  .select('treecover2000')
  .clip(studyArea)
  .rename('Tree_Cover_Pct');

print('✓ LULC loaded: ESA WorldCover, Dynamic World, GAIA, Hansen.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 9: ERA5-LAND WEATHER DATA                                           █
// ████████████████████████████████████████████████████████████████████████████████
// ERA5-Land reanalysis at ~11 km hourly resolution.
// Variables averaged over the study period.

var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE);

print('ERA5-Land hourly records:', era5.size());

// ─── 9a. Air Temperature (K → °C) ──────────────────────────────────────────
var airTempK = era5.select('temperature_2m').mean();
var airTemp = airTempK.subtract(273.15).clip(studyArea).rename('AirTemp');

// ─── 9b. Relative Humidity (Magnus formula) ────────────────────────────────
// RH = 100 × exp[(17.625×Td)/(243.04+Td)] / exp[(17.625×T)/(243.04+T)]
var dewpointK = era5.select('dewpoint_temperature_2m').mean();
var dewpointC = dewpointK.subtract(273.15);
var airTempC  = airTempK.subtract(273.15);
var rhNum = dewpointC.multiply(17.625).divide(dewpointC.add(243.04));
var rhDen = airTempC.multiply(17.625).divide(airTempC.add(243.04));
var humidity = rhNum.subtract(rhDen).exp().multiply(100)
  .clamp(0, 100).clip(studyArea).rename('Humidity');

// ─── 9c. Wind Speed (m/s) ──────────────────────────────────────────────────
var windU = era5.select('u_component_of_wind_10m').mean();
var windV = era5.select('v_component_of_wind_10m').mean();
var windSpeed = windU.pow(2).add(windV.pow(2)).sqrt()
  .clip(studyArea).rename('WindSpeed');

// ─── 9d. Wind Direction (degrees, meteorological convention) ────────────────
// Direction FROM which wind blows: atan2(-U, -V) × (180/π) + 180
var windDirection = windU.multiply(-1).atan2(windV.multiply(-1))
  .multiply(180 / Math.PI).add(180).mod(360)
  .clip(studyArea).rename('WindDirection');

// ─── 9e. Solar Radiation (J/m²/hour → W/m²) ────────────────────────────────
// Hourly accumulation in J/m². Divide by 3600 to get average watts.
var solarRad = era5.select('surface_solar_radiation_downwards_hourly')
  .mean().divide(3600).clip(studyArea).rename('SolarRadiation');

// ─── 9f. Surface Pressure (Pa → hPa) ───────────────────────────────────────
var pressure = era5.select('surface_pressure')
  .mean().divide(100).clip(studyArea).rename('Pressure');

// ─── 9g. Rainfall (m/hour → mm total accumulated) ──────────────────────────
var rainfall = era5.select('total_precipitation_hourly')
  .sum().multiply(1000).clip(studyArea).rename('Rainfall');

print('✓ ERA5 weather: AirTemp, Humidity, WindSpeed, WindDir, ' +
  'Solar, Pressure, Rainfall.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 10: TERRAIN — SRTM ELEVATION, SLOPE, ASPECT                        █
// ████████████████████████████████████████████████████████████████████████████████
// SRTM v3 at 30m resolution. Terrain features affect air flow and heat retention.

var srtm = ee.Image('USGS/SRTMGL1_003').clip(studyArea);
var terrain = ee.Terrain.products(srtm);

var elevation = terrain.select('elevation').rename('Elevation');
var slope     = terrain.select('slope').rename('Slope');
var aspect    = terrain.select('aspect').rename('Aspect');

print('✓ Terrain: Elevation, Slope, Aspect from SRTM 30m.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 11: URBAN MORPHOLOGY                                                █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 11a. GHSL Built-up Surface (Building Density) ─────────────────────────
// Built-up surface fraction from the Global Human Settlement Layer.
// Note: If this collection ID errors, check the GEE catalog for the
// latest GHSL path (it may include epoch/resolution suffixes).
var buildingDensity;
try {
  var ghslBuilt = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S')
    .mosaic().clip(studyArea);
  buildingDensity = ghslBuilt.select(0).rename('Building_Density');
} catch(e) {
  print('⚠ GHSL Built-up Surface not found. Using WorldCover built-up proxy.');
  buildingDensity = worldCover.eq(50).rename('Building_Density');
}

// ─── 11b. GHSL Building Height ──────────────────────────────────────────────
var buildingHeight;
try {
  var ghslHeight = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_H')
    .mosaic().clip(studyArea);
  buildingHeight = ghslHeight.select(0).rename('Building_Height');
} catch(e) {
  print('⚠ GHSL Building Height not found. Using constant estimate (10m).');
  buildingHeight = ee.Image.constant(10).clip(studyArea).rename('Building_Height');
}

// ─── 11c. Building Volume Proxy ─────────────────────────────────────────────
// Volume = footprint area × height. Both are per-pixel, so just multiply.
var buildingVolume = buildingDensity.multiply(buildingHeight)
  .rename('Building_Volume');

// ─── 11d. VIIRS Nighttime Lights ────────────────────────────────────────────
// Monthly VIIRS DNB radiance (nW/cm²/sr). Proxy for urban activity.
var viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')
  .filterDate(START_DATE, END_DATE)
  .select('avg_rad');
var nightLights = viirs.median().clip(studyArea)
  .max(0)                            // Remove negative radiance artifacts
  .rename('Nighttime_Lights');

// ─── 11e. Population Density (WorldPop 100m) ────────────────────────────────
// UN-adjusted 100m gridded population for India.
var worldPop = ee.ImageCollection('WorldPop/GP/100m/pop')
  .filterDate(String(POP_YEAR) + '-01-01', String(POP_YEAR) + '-12-31')
  .filter(ee.Filter.eq('country', 'IND'))
  .mosaic()
  .clip(studyArea)
  .rename('Population_Density');

print('✓ Urban morphology: Buildings, VIIRS, Population.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 12: DERIVED SPATIAL FEATURES                                        █
// ████████████████████████████████████████████████████████████████████████████████

// ─── 12a. Distance to Water (meters) ────────────────────────────────────────
// Euclidean distance from each pixel to the nearest water pixel (NDWI > 0).
// fastDistanceTransform returns squared distance in pixels; sqrt → linear.
var waterMask = ndwi.gt(0).selfMask();
var distWater = waterMask.fastDistanceTransform(512).sqrt()
  .multiply(EXPORT_SCALE)            // Convert pixel distance to meters
  .clip(studyArea)
  .rename('Dist_Water');

// ─── 12b. Distance to Green Space (meters) ──────────────────────────────────
// Distance to nearest pixel with NDVI > 0.4 (moderate-dense vegetation).
var greenMask = ndvi.gt(0.4).selfMask();
var distGreen = greenMask.fastDistanceTransform(512).sqrt()
  .multiply(EXPORT_SCALE)
  .clip(studyArea)
  .rename('Dist_Green');

// ─── 12c. Green Space Density (fraction) ────────────────────────────────────
// Fraction of pixels with NDVI > 0.3 within a 150m circular neighborhood.
var greenBinary = ndvi.gt(0.3);
var kernel = ee.Kernel.circle({radius: KERNEL_RADIUS, units: 'pixels'});
var greenDensity = greenBinary.reduceNeighborhood({
  reducer: ee.Reducer.mean(),
  kernel: kernel
}).rename('Green_Space_Density');

// ─── 12d. Surface Roughness Proxy ───────────────────────────────────────────
// Std-dev of elevation in neighborhood. High roughness → complex terrain.
var surfaceRoughness = elevation.reduceNeighborhood({
  reducer: ee.Reducer.stdDev(),
  kernel: kernel
}).rename('Surface_Roughness');

// ─── 12e. Anthropogenic Heat Proxy ──────────────────────────────────────────
// Proxy = NighttimeLights(normalized) × Population(normalized).
// Scientific basis: light + people → waste heat from buildings/vehicles.
var ntlNorm = nightLights.unitScale(0, 100);
var popNorm = worldPop.unitScale(0, 10000);
var anthropogenicHeat = ntlNorm.multiply(popNorm)
  .rename('Anthropogenic_Heat');

// ─── 12f. Road Density Proxy ────────────────────────────────────────────────
// Estimated as: impervious surface MINUS built-up footprint.
// Roads are impervious but not buildings. This is a rough proxy.
var roadProxy = impervious.subtract(worldCover.eq(50))
  .max(0)
  .rename('Road_Density_Proxy');

print('✓ Derived features: Dist_Water, Dist_Green, Green_Density, ' +
  'Roughness, Anthropogenic_Heat, Road_Proxy.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 13: RESAMPLE & COMBINE ALL FEATURES                                 █
// ████████████████████████████████████████████████████████████████████████████████
// ERA5, WorldPop, GHSL, and VIIRS are at coarser resolutions.
// Bilinear interpolation aligns them to the 30m Landsat grid.
// Categorical layers (LULC) use nearest-neighbor to preserve class values.

// Helper: resample a continuous layer to the target scale.
function resampleContinuous(image) {
  return image.resample('bilinear')
    .reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});
}

// Helper: resample a categorical layer (nearest neighbor, no interpolation).
function resampleCategorical(image) {
  return image.reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});
}

// Resample coarse-resolution layers.
var airTempR     = resampleContinuous(airTemp);
var humidityR    = resampleContinuous(humidity);
var windSpeedR   = resampleContinuous(windSpeed);
var windDirR     = resampleContinuous(windDirection);
var solarRadR    = resampleContinuous(solarRad);
var pressureR    = resampleContinuous(pressure);
var rainfallR    = resampleContinuous(rainfall);
var buildDensR   = resampleContinuous(buildingDensity);
var buildHeightR = resampleContinuous(buildingHeight);
var buildVolR    = resampleContinuous(buildingVolume);
var nightLightsR = resampleContinuous(nightLights);
var popDensR     = resampleContinuous(worldPop);
var anthroHeatR  = resampleContinuous(anthropogenicHeat);

// Resample categorical layers (nearest neighbor).
var lulcESAr = resampleCategorical(lulcESA);
var lulcDWr  = resampleCategorical(lulcDW);

// ─── Combine into one master multi-band image ───────────────────────────────
var masterImage = lst
  // Spectral Indices
  .addBands(ndvi)
  .addBands(ndbi)
  .addBands(ndwi)
  .addBands(mndwi)
  .addBands(savi)
  .addBands(albedo)
  // Land Cover
  .addBands(lulcESAr)
  .addBands(lulcDWr)
  .addBands(impervious)
  .addBands(treeCover)
  // Weather
  .addBands(airTempR)
  .addBands(humidityR)
  .addBands(windSpeedR)
  .addBands(windDirR)
  .addBands(solarRadR)
  .addBands(pressureR)
  .addBands(rainfallR)
  // Terrain
  .addBands(elevation)
  .addBands(slope)
  .addBands(aspect)
  // Urban Morphology
  .addBands(buildDensR)
  .addBands(buildHeightR)
  .addBands(buildVolR)
  .addBands(nightLightsR)
  .addBands(popDensR)
  // Distance Features
  .addBands(distWater)
  .addBands(distGreen)
  // Density & Proxy Features
  .addBands(greenDensity)
  .addBands(surfaceRoughness)
  .addBands(anthroHeatR)
  .addBands(roadProxy)
  // Heat Indices
  .addBands(uhiIntensity)
  .addBands(utfvi)
  // Quality
  .addBands(landsatCount);

print('✓ Master image created with', masterImage.bandNames().size(), 'bands:');
print(masterImage.bandNames());


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 14: MAP VISUALIZATION                                               █
// ████████████████████████████████████████████████████████████████████████████████
// All layers are added to the map with scientific color palettes.
// Layers default to off (false) except LST and UHI Intensity.

// ─── Color palette definitions ──────────────────────────────────────────────
var palLST  = ['1a3678','2955bc','5699ff','8dbae9','acd1ff','caebf2',
               'e0f3db','a8ddb5','7bccc4','f7fcb9','fff7bc','fec44f',
               'fe9929','ec7014','cc4c02','993404','662506'];
var palNDVI = ['d73027','f46d43','fdae61','fee08b','d9ef8b','a6d96a',
               '66bd63','1a9850','006837'];
var palNDBI = ['2166ac','67a9cf','d1e5f0','fddbc7','ef8a62','b2182b'];
var palNDWI = ['d73027','fc8d59','fee090','e0f3f8','91bfdb','4575b4'];
var palUHI  = ['313695','4575b4','74add1','abd9e9','e0f3f8',
               'ffffbf','fee090','fdae61','f46d43','d73027','a50026'];
var palElev = ['006837','1a9850','66bd63','a6d96a','d9ef8b',
               'fee08b','fdae61','f46d43','d73027'];
var palNTL  = ['000000','1a1a2e','16213e','0f3460',
               '533483','e94560','f38181','fce38a','eaffd0'];
var palPop  = ['ffffcc','ffeda0','fed976','feb24c','fd8d3c',
               'fc4e2a','e31a1c','bd0026','800026'];

// ─── Satellite Composites ───────────────────────────────────────────────────
Map.addLayer(landsatComposite,
  {bands: ['SR_B4','SR_B3','SR_B2'], min: 0, max: 0.3},
  'Landsat True Color', false);
Map.addLayer(s2Composite,
  {bands: ['B4','B3','B2'], min: 0, max: 0.3},
  'Sentinel-2 True Color', false);

// ─── Land Surface Temperature ───────────────────────────────────────────────
Map.addLayer(lst, {min: 25, max: 55, palette: palLST},
  '🌡 LST (°C)', true);

// ─── UHI Intensity ──────────────────────────────────────────────────────────
Map.addLayer(uhiIntensity, {min: -5, max: 10, palette: palUHI},
  '🔥 UHI Intensity (°C)', true);

// ─── UTFVI ──────────────────────────────────────────────────────────────────
Map.addLayer(utfvi, {min: -0.05, max: 0.05, palette: palUHI},
  'UTFVI', false);

// ─── Spectral Indices ───────────────────────────────────────────────────────
Map.addLayer(ndvi,  {min: -0.2, max: 0.8, palette: palNDVI}, 'NDVI', false);
Map.addLayer(ndbi,  {min: -0.3, max: 0.3, palette: palNDBI}, 'NDBI', false);
Map.addLayer(ndwi,  {min: -0.5, max: 0.5, palette: palNDWI}, 'NDWI', false);
Map.addLayer(mndwi, {min: -0.5, max: 0.5, palette: palNDWI}, 'MNDWI', false);
Map.addLayer(albedo,{min: 0.05, max: 0.4, palette: ['000000','ffffff']},
  'Albedo', false);
Map.addLayer(ndviS2,{min: -0.2, max: 0.8, palette: palNDVI},
  'NDVI Sentinel-2 (10m)', false);

// ─── Land Cover ─────────────────────────────────────────────────────────────
Map.addLayer(lulcESA, {min: 10, max: 100,
  palette: ['006400','ffbb22','ffff4c','f096ff','fa0000','b4b4b4',
            'f0f0f0','0064c8','0096a0','00cf75','fae6a0']},
  'LULC ESA WorldCover', false);
Map.addLayer(lulcDW, {min: 0, max: 8,
  palette: ['419bdf','397d49','88b053','7a87c6','e49635',
            'dfc35a','c4281b','a59b8f','b39fe1']},
  'LULC Dynamic World', false);
Map.addLayer(impervious, {min: 0, max: 1, palette: ['white','red']},
  'Impervious Surface', false);
Map.addLayer(treeCover, {min: 0, max: 80, palette: palNDVI},
  'Tree Cover %', false);

// ─── Weather ────────────────────────────────────────────────────────────────
Map.addLayer(airTemp,  {min: 25, max: 45, palette: ['blue','cyan','yellow','red']},
  'Air Temperature (°C)', false);
Map.addLayer(humidity, {min: 20, max: 90, palette: ['ffffcc','a1dab4','41b6c4','225ea8']},
  'Relative Humidity (%)', false);
Map.addLayer(windSpeed,{min: 0, max: 6, palette: ['ffffff','c6dbef','6baed6','08306b']},
  'Wind Speed (m/s)', false);
Map.addLayer(solarRad, {min: 100, max: 350, palette: ['f7fcf5','d9f0a3','78c679','006837']},
  'Solar Radiation (W/m²)', false);

// ─── Terrain ────────────────────────────────────────────────────────────────
Map.addLayer(elevation,{min: 150, max: 350, palette: palElev},
  'Elevation (m)', false);
Map.addLayer(slope,    {min: 0, max: 15, palette: ['white','brown']},
  'Slope (°)', false);

// ─── Urban Morphology ───────────────────────────────────────────────────────
Map.addLayer(nightLights,{min: 0, max: 60, palette: palNTL},
  'Nighttime Lights', false);
Map.addLayer(worldPop,{min: 0, max: 500, palette: palPop},
  'Population Density', false);

// ─── Distance Features ──────────────────────────────────────────────────────
Map.addLayer(distWater,{min: 0, max: 5000, palette: ['4575b4','abd9e9','fee090','d73027']},
  'Distance to Water (m)', false);
Map.addLayer(distGreen,{min: 0, max: 3000, palette: ['006837','a6d96a','fee08b','d73027']},
  'Distance to Green (m)', false);

// ─── Derived Features ───────────────────────────────────────────────────────
Map.addLayer(greenDensity,{min: 0, max: 1, palette: ['d73027','fee08b','006837']},
  'Green Space Density', false);
Map.addLayer(landsatCount,{min: 0, max: 20, palette: ['red','yellow','green']},
  'Quality Score (obs count)', false);

print('✓ All layers added to map.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 15: EXPORT GeoTIFF FILES                                            █
// ████████████████████████████████████████████████████████████████████████████████
// Each layer exported as a separate GeoTIFF to Google Drive.
// After clicking "Run", go to the Tasks tab and click "Run" on each task.

function exportTIFF(img, desc, name) {
  Export.image.toDrive({
    image: img, description: desc,
    folder: DRIVE_FOLDER,
    fileNamePrefix: CITY_NAME + '_' + name,
    region: studyArea, scale: EXPORT_SCALE,
    crs: 'EPSG:4326', maxPixels: 1e13,
    fileFormat: 'GeoTIFF'
  });
}

// Satellite Indices
exportTIFF(lst,     'Export_LST',     'LST');
exportTIFF(ndvi,    'Export_NDVI',    'NDVI');
exportTIFF(ndbi,    'Export_NDBI',    'NDBI');
exportTIFF(ndwi,    'Export_NDWI',    'NDWI');
exportTIFF(mndwi,   'Export_MNDWI',   'MNDWI');
exportTIFF(savi,    'Export_SAVI',    'SAVI');
exportTIFF(albedo,  'Export_Albedo',  'Albedo');

// Land Cover
exportTIFF(lulcESA,    'Export_LULC_ESA',     'LULC_ESA');
exportTIFF(lulcDW,     'Export_LULC_DW',      'LULC_DW');
exportTIFF(impervious, 'Export_Impervious',    'Impervious');
exportTIFF(treeCover,  'Export_TreeCover',     'TreeCover');

// Weather
exportTIFF(airTemp,   'Export_AirTemp',       'AirTemp');
exportTIFF(humidity,  'Export_Humidity',       'Humidity');
exportTIFF(windSpeed, 'Export_WindSpeed',      'WindSpeed');
exportTIFF(windDirection,'Export_WindDir',     'WindDirection');
exportTIFF(solarRad,  'Export_SolarRad',      'SolarRadiation');
exportTIFF(pressure,  'Export_Pressure',      'Pressure');
exportTIFF(rainfall,  'Export_Rainfall',      'Rainfall');

// Terrain
exportTIFF(elevation, 'Export_Elevation',     'Elevation');
exportTIFF(slope,     'Export_Slope',         'Slope');
exportTIFF(aspect,    'Export_Aspect',        'Aspect');

// Urban Morphology
exportTIFF(buildingDensity,'Export_BuildDensity','Building_Density');
exportTIFF(buildingHeight, 'Export_BuildHeight', 'Building_Height');
exportTIFF(nightLights,    'Export_NightLights', 'Nighttime_Lights');
exportTIFF(worldPop,       'Export_Population',  'Population_Density');

// Distance & Derived
exportTIFF(distWater,       'Export_DistWater',      'Dist_Water');
exportTIFF(distGreen,       'Export_DistGreen',      'Dist_Green');
exportTIFF(greenDensity,    'Export_GreenDensity',   'Green_Space_Density');
exportTIFF(surfaceRoughness,'Export_Roughness',      'Surface_Roughness');
exportTIFF(anthropogenicHeat,'Export_AnthroHeat',    'Anthropogenic_Heat');

// Heat Indices
exportTIFF(uhiIntensity,'Export_UHI',  'UHI_Intensity');
exportTIFF(utfvi,       'Export_UTFVI','UTFVI');

// Quality
exportTIFF(landsatCount,'Export_Quality','QualityScore');

// Satellite Composites (multi-band)
Export.image.toDrive({
  image: landsatComposite.select(['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']),
  description: 'Export_Landsat_Composite',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_Landsat_Composite',
  region: studyArea, scale: 30, crs: 'EPSG:4326',
  maxPixels: 1e13, fileFormat: 'GeoTIFF'
});

Export.image.toDrive({
  image: s2Composite.select(['B2','B3','B4','B8','B11','B12']),
  description: 'Export_Sentinel2_Composite',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_Sentinel2_Composite',
  region: studyArea, scale: 10, crs: 'EPSG:4326',
  maxPixels: 1e13, fileFormat: 'GeoTIFF'
});

print('✓ ' + 32 + ' GeoTIFF export tasks created. Go to Tasks tab → Run all.');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 16: CSV EXPORT — AI-READY MASTER DATASET                            █
// ████████████████████████████████████████████████████████████████████████████████
// Sample the master image at regular grid points.
// Each row = one geographic location with ALL 35+ feature values.
// This CSV is the primary training dataset for ML models.

// ─── 16a. Sample the Master Image ───────────────────────────────────────────
var samplePoints = masterImage.sample({
  region: studyArea,
  scale: CSV_SAMPLE_SCALE,
  numPixels: MAX_CSV_POINTS,
  seed: 42,
  geometries: true                   // Keep coordinates for lat/lon extraction
});

// ─── 16b. Add Latitude, Longitude, PixelID, Timestamp ───────────────────────
var sampleWithCoords = samplePoints.map(function(feature) {
  var coords = feature.geometry().coordinates();
  return feature
    .set('Longitude', coords.get(0))
    .set('Latitude', coords.get(1))
    .set('Timestamp', START_DATE + '_to_' + END_DATE);
});

// Add sequential PixelID.
var sampleList = sampleWithCoords.toList(MAX_CSV_POINTS);
var withIDs = ee.FeatureCollection(
  sampleList.map(function(feat) {
    var idx = sampleList.indexOf(feat);
    return ee.Feature(feat).set('PixelID', idx);
  })
);

// ─── 16c. Select Final Columns ──────────────────────────────────────────────
// Explicitly define the column order for the CSV.
var csvColumns = [
  'PixelID', 'Latitude', 'Longitude', 'Timestamp',
  // Target
  'LST',
  // Spectral Indices
  'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo',
  // Land Cover
  'LULC_ESA', 'LULC_DW', 'Impervious_Frac', 'Tree_Cover_Pct',
  // Weather
  'AirTemp', 'Humidity', 'WindSpeed', 'WindDirection',
  'SolarRadiation', 'Pressure', 'Rainfall',
  // Terrain
  'Elevation', 'Slope', 'Aspect',
  // Urban Morphology
  'Building_Density', 'Building_Height', 'Building_Volume',
  'Nighttime_Lights', 'Population_Density',
  // Distance
  'Dist_Water', 'Dist_Green',
  // Derived
  'Green_Space_Density', 'Surface_Roughness',
  'Anthropogenic_Heat', 'Road_Density_Proxy',
  // Heat Indices
  'UHI_Intensity', 'UTFVI',
  // Quality
  'QualityScore'
];

var csvData = withIDs.select({
  propertyNames: csvColumns,
  retainGeometry: false
});

// ─── 16d. Print Preview ─────────────────────────────────────────────────────
print('CSV sample count:', csvData.size());
print('CSV preview (first 3 rows):', csvData.limit(3));
print('CSV columns (' + csvColumns.length + '):', csvColumns);

// ─── 16e. Export CSV ────────────────────────────────────────────────────────
Export.table.toDrive({
  collection: csvData,
  description: 'Export_MasterCSV',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_UHI_MasterDataset',
  fileFormat: 'CSV'
});

print('✓ Master CSV export task created (' + csvColumns.length + ' columns).');


// ████████████████████████████████████████████████████████████████████████████████
// █  SECTION 17: PIPELINE SUMMARY & VALIDATION                                   █
// ████████████████████████████████████████████████████████████████████████████████

print('');
print('╔══════════════════════════════════════════════════════════════╗');
print('║            URBAN HEAT AI — PIPELINE COMPLETE                ║');
print('╚══════════════════════════════════════════════════════════════╝');
print('');
print('City:            ', CITY_NAME);
print('Date Range:      ', START_DATE, 'to', END_DATE);
print('Export Scale:     ', EXPORT_SCALE, 'meters');
print('CSV Sample Scale: ', CSV_SAMPLE_SCALE, 'meters');
print('Drive Folder:    ', DRIVE_FOLDER);
print('');
print('── Data Sources ───────────────────────────────────────────────');
print('  Landsat-8 C2 L2       ✓');
print('  Landsat-9 C2 L2       ✓');
print('  Sentinel-2 SR         ✓');
print('  ERA5-Land Hourly      ✓');
print('  ESA WorldCover        ✓');
print('  Dynamic World         ✓');
print('  GAIA Impervious       ✓');
print('  Hansen Forest Change  ✓');
print('  SRTM 30m DEM          ✓');
print('  GHSL Built-up         ✓');
print('  GHSL Building Height  ✓');
print('  VIIRS Nighttime       ✓');
print('  WorldPop              ✓');
print('');
print('── Computed Features (' + csvColumns.length + ') ───────────────────────────────');
print('  Spectral:  LST, NDVI, NDBI, NDWI, MNDWI, Albedo');
print('  Land Use:  LULC_ESA, LULC_DW, Impervious, TreeCover');
print('  Weather:   AirTemp, Humidity, Wind, WindDir, Solar, Pressure, Rain');
print('  Terrain:   Elevation, Slope, Aspect');
print('  Urban:     BuildDensity, BuildHeight, BuildVol, NightLights, Pop');
print('  Distance:  Dist_Water, Dist_Green');
print('  Derived:   GreenDensity, Roughness, AnthroHeat, RoadProxy');
print('  Heat:      UHI_Intensity, UTFVI');
print('  Quality:   QualityScore');
print('');
print('── Exports (33 GeoTIFF + 1 CSV) ─────────────────────────────');
print('  Go to TASKS tab (top-right) → Click RUN on each task.');
print('  Files will appear in Google Drive → ' + DRIVE_FOLDER);
print('');
print('── Next Steps ─────────────────────────────────────────────────');
print('  1. Run all export tasks in the Tasks tab');
print('  2. Download CSV from Google Drive');
print('  3. Use CSV for ML training (pandas/sklearn/xgboost/pytorch)');
print('  4. Target variable = LST; Features = everything else');
print('══════════════════════════════════════════════════════════════');
