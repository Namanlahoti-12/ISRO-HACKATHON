// ============================================================================
// URBAN HEAT STRESS MAPPING — DATA COLLECTION & PREPROCESSING PIPELINE
// ============================================================================
// Project  : ISRO Bharatiya Antariksh Hackathon
// Purpose  : Collect and preprocess satellite + weather data to identify
//            Urban Heat Island (UHI) hotspots in Indian cities.
// Author   : AI-assisted pipeline
// Date     : June 2026
//
// HOW TO USE THIS SCRIPT:
//   1. Open https://code.earthengine.google.com
//   2. Create a new script (File → New)
//   3. Copy-paste this ENTIRE file into the code editor
//   4. Modify the CONFIGURATION section below for your city
//   5. Click "Run"
//   6. Check the "Tasks" tab (top-right) to start exports
//
// IMPORTANT: You need a Google Earth Engine account.
//   Sign up free at https://earthengine.google.com/signup/
// ============================================================================


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 1: CONFIGURATION — CHANGE THESE VALUES FOR YOUR CITY           ║
// ╚═══════════════════════════════════════════════════════════════════════════╝

// --- 1a. City Selection ---
// Option A: Use latitude/longitude with a buffer (radius in meters).
//   This creates a circular study area around the city center.
//   Find coordinates from Google Maps: right-click any location → copy coords.

var CITY_NAME = 'Delhi';           // Name used in exported file names
var CENTER_LAT = 28.6139;          // Latitude of the city center
var CENTER_LON = 77.2090;          // Longitude of the city center
var BUFFER_RADIUS_M = 25000;       // Buffer radius in meters (25 km)

// Option B: Use an administrative boundary instead.
//   Set USE_ADMIN_BOUNDARY to true and specify the district/city name.
//   The script will look up the boundary from the FAO GAUL dataset.

var USE_ADMIN_BOUNDARY = false;    // Set to true to use admin boundary
var ADMIN_DISTRICT_NAME = 'Delhi'; // District name in GAUL dataset

// --- 1b. Date Range ---
// Choose the time period for satellite image collection.
// For heat studies in India, use summer months (March–June).
// A wider range gives more cloud-free images to build a good composite.

var START_DATE = '2024-03-01';     // Start date (YYYY-MM-DD format)
var END_DATE   = '2024-06-30';     // End date   (YYYY-MM-DD format)

// --- 1c. Cloud Cover Threshold ---
// Only keep images where cloud cover is below this percentage.
// Lower = stricter (fewer images but cleaner), Higher = more images.

var MAX_CLOUD_PERCENT = 20;        // Maximum acceptable cloud cover (%)

// --- 1d. Export Settings ---
// Resolution in meters for exported GeoTIFF and CSV files.
// 30m matches Landsat native resolution (recommended).

var EXPORT_SCALE = 30;             // Pixel size in meters for exports

// Folder name in your Google Drive where files will be saved.
var DRIVE_FOLDER = 'ISRO_UHI_Data';

// --- 1e. CSV Sampling ---
// Exporting every pixel as CSV can create very large files.
// We sample a grid of points instead. Adjust spacing as needed.
// 100m spacing = ~1 point per 100m × 100m area.

var CSV_SAMPLE_SCALE = 100;        // Spacing between sample points (meters)
var MAX_CSV_POINTS = 100000;       // Maximum number of points in CSV


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 2: DEFINE THE STUDY AREA                                       ║
// ╚═══════════════════════════════════════════════════════════════════════════╝

// Create a point geometry from the latitude and longitude.
// ee.Geometry.Point takes [longitude, latitude] — note the order!
var cityCenter = ee.Geometry.Point([CENTER_LON, CENTER_LAT]);

// Define the study area (Region of Interest).
var studyArea;

if (USE_ADMIN_BOUNDARY) {
  // --- Option B: Administrative Boundary ---
  // FAO GAUL Level 2 provides district-level boundaries worldwide.
  // We filter it to find the district matching our name.
  var gaul = ee.FeatureCollection('FAO/GAUL/2015/level2');

  // Filter to India first (ADM0_NAME = country name), then to the district.
  var district = gaul
    .filter(ee.Filter.eq('ADM0_NAME', 'India'))          // Country = India
    .filter(ee.Filter.eq('ADM2_NAME', ADMIN_DISTRICT_NAME)); // District name

  // Use the geometry (shape) of the matched district as our study area.
  studyArea = district.geometry();

  // Print to console so you can verify the boundary was found.
  print('Admin boundary found:', district.first().get('ADM2_NAME'));

} else {
  // --- Option A: Circular Buffer ---
  // Create a circle around the city center with the specified radius.
  // .buffer(radius) expands the point into a circle.
  studyArea = cityCenter.buffer(BUFFER_RADIUS_M);
}

// Center the map on our study area and zoom to fit.
// Zoom level 11 works well for a city-scale view.
Map.centerObject(studyArea, 11);

// Draw the study area boundary on the map (yellow outline, no fill).
Map.addLayer(
  ee.Image().paint(ee.FeatureCollection([ee.Feature(studyArea)]), 0, 2),
  {palette: ['FFFF00']},  // Yellow color
  'Study Area Boundary'   // Layer name shown in the map panel
);

// Print the study area size so we know how large it is.
print('Study Area (sq km):', studyArea.area().divide(1e6));


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 3: LANDSAT-8 — LOAD, CLOUD MASK, AND PREPROCESS               ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Landsat-8 Collection 2, Level 2 provides:
//   - Surface Reflectance (SR) bands for vegetation/built-up indices
//   - Surface Temperature (ST) band for Land Surface Temperature
// Level 2 = already atmospherically corrected by USGS (ready to use).

// --- 3a. Cloud Masking Function for Landsat-8 ---
// The QA_PIXEL band contains bit-packed quality flags.
// We check specific bits to identify clouds and cloud shadows.
// Bit 3 = Cloud Shadow, Bit 4 = Cloud.
// If either bit is set (= 1), the pixel is cloudy → we mask it out.

function maskLandsatClouds(image) {
  // Read the QA_PIXEL band from the image.
  var qa = image.select('QA_PIXEL');

  // Bit 3 (cloud shadow) and Bit 4 (cloud):
  // bitwiseAnd checks if a specific bit is set.
  // If the bit is 0, the pixel is clear.
  var cloudShadowBit = 1 << 3;  // = 8 in decimal  (binary: 1000)
  var cloudBit       = 1 << 4;  // = 16 in decimal (binary: 10000)

  // A pixel is "clear" if BOTH cloud shadow AND cloud bits are 0.
  // .bitwiseAnd(bit).eq(0) checks that the bit is NOT set.
  var clearMask = qa.bitwiseAnd(cloudShadowBit).eq(0)  // No cloud shadow
                    .and(qa.bitwiseAnd(cloudBit).eq(0)); // No cloud

  // .updateMask() keeps only pixels where clearMask = 1 (true).
  // Masked pixels become transparent/null in calculations.
  return image.updateMask(clearMask);
}

// --- 3b. Scaling Function for Landsat-8 ---
// Raw pixel values in the collection are stored as integers to save space.
// We must apply scale factors to convert them to physical units.
//   Surface Reflectance: multiply by 0.0000275, then add -0.2
//   Surface Temperature: multiply by 0.00341802, then add 149.0 (gives Kelvin)

function scaleLandsat(image) {
  // Select the optical/reflectance bands (SR_B1 through SR_B7).
  var opticalBands = image.select('SR_B.*')           // Regex: all SR_B bands
                          .multiply(0.0000275)         // Apply scale factor
                          .add(-0.2);                  // Apply offset

  // Select the thermal/temperature band (ST_B10).
  var thermalBand = image.select('ST_B10')
                         .multiply(0.00341802)         // Apply scale factor
                         .add(149.0);                  // Apply offset → Kelvin

  // Replace the original bands with the scaled versions.
  // .addBands with overwrite=true replaces bands with the same name.
  return image.addBands(opticalBands, null, true)
              .addBands(thermalBand, null, true);
}

// --- 3c. Load the Landsat-8 Image Collection ---
var landsat8Raw = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .filterBounds(studyArea)           // Only images covering our study area
  .filterDate(START_DATE, END_DATE)  // Only images in our date range
  .filter(ee.Filter.lt(              // Only images with low cloud cover
    'CLOUD_COVER', MAX_CLOUD_PERCENT
  ));

// Print how many images we found (useful for debugging).
print('Landsat-8 images found:', landsat8Raw.size());

// --- 3d. Apply Cloud Masking and Scaling ---
// .map() applies a function to every image in the collection.
// First scale, then mask clouds.
var landsat8Processed = landsat8Raw
  .map(scaleLandsat)        // Step 1: Convert to physical units
  .map(maskLandsatClouds);  // Step 2: Remove cloudy pixels

// --- 3e. Create Median Composite ---
// .median() takes the median value across all images for each pixel.
// This produces a single, cloud-free "best" image.
// Median is robust to outliers (e.g., remaining cloud edges).
var landsat8Composite = landsat8Processed
  .median()                 // Pixel-wise median across all images
  .clip(studyArea);         // Clip to our study area boundary

print('Landsat-8 composite created successfully.');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 4: SENTINEL-2 — LOAD, CLOUD MASK, AND PREPROCESS              ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Sentinel-2 provides higher resolution (10m) optical imagery.
// We use the Surface Reflectance (SR) Harmonized collection.
// "Harmonized" means band names are consistent across S2A and S2B sensors.

// --- 4a. Cloud Masking Function for Sentinel-2 ---
// Sentinel-2 uses the QA60 band for cloud information.
// Bit 10 = Opaque clouds, Bit 11 = Cirrus clouds.

function maskS2Clouds(image) {
  var qa = image.select('QA60');

  var opaqueBit = 1 << 10;   // Bit 10: opaque clouds
  var cirrusBit = 1 << 11;   // Bit 11: cirrus clouds

  // Keep pixels where NEITHER cloud bit is set.
  var clearMask = qa.bitwiseAnd(opaqueBit).eq(0)
                    .and(qa.bitwiseAnd(cirrusBit).eq(0));

  // Also apply the existing cloud probability if available.
  return image.updateMask(clearMask);
}

// --- 4b. Scaling Function for Sentinel-2 ---
// Sentinel-2 SR values are stored as integers (0–10000).
// Divide by 10000 to get reflectance values between 0 and 1.

function scaleS2(image) {
  var scaled = image.select(['B2','B3','B4','B8','B11','B12'])
                    .divide(10000);  // Convert to 0–1 reflectance range

  // Return the scaled bands, keeping original metadata and other bands.
  return image.addBands(scaled, null, true);
}

// --- 4c. Load the Sentinel-2 Image Collection ---
var sentinel2Raw = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE)
  .filter(ee.Filter.lt(
    'CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD_PERCENT
  ));

print('Sentinel-2 images found:', sentinel2Raw.size());

// --- 4d. Apply Cloud Masking and Scaling ---
var sentinel2Processed = sentinel2Raw
  .map(scaleS2)
  .map(maskS2Clouds);

// --- 4e. Create Median Composite ---
var sentinel2Composite = sentinel2Processed
  .median()
  .clip(studyArea);

print('Sentinel-2 composite created successfully.');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 5: CALCULATE SPECTRAL INDICES                                  ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Spectral indices help us understand what is on the ground:
//   NDVI → vegetation health (higher = more green vegetation)
//   NDBI → built-up/urban areas (higher = more concrete/buildings)
//   NDWI → water bodies (higher = more water)
//   LST  → land surface temperature (how hot the ground is)

// --- 5a. NDVI (Normalized Difference Vegetation Index) ---
// Formula: NDVI = (NIR - Red) / (NIR + Red)
// Landsat-8: NIR = SR_B5, Red = SR_B4
// Range: -1 to +1. Values > 0.3 indicate healthy vegetation.

var ndvi = landsat8Composite.normalizedDifference(['SR_B5', 'SR_B4'])
                            .rename('NDVI');
// .normalizedDifference([A, B]) computes (A - B) / (A + B) automatically.

print('NDVI range:', ndvi.reduceRegion({
  reducer: ee.Reducer.minMax(),  // Get minimum and maximum values
  geometry: studyArea,
  scale: 30,
  maxPixels: 1e9
}));

// --- 5b. NDBI (Normalized Difference Built-up Index) ---
// Formula: NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
// Landsat-8: SWIR1 = SR_B6, NIR = SR_B5
// Range: -1 to +1. Positive values indicate built-up areas.

var ndbi = landsat8Composite.normalizedDifference(['SR_B6', 'SR_B5'])
                            .rename('NDBI');

print('NDBI range:', ndbi.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: studyArea,
  scale: 30,
  maxPixels: 1e9
}));

// --- 5c. NDWI (Normalized Difference Water Index) ---
// Formula: NDWI = (Green - NIR) / (Green + NIR)
// Landsat-8: Green = SR_B3, NIR = SR_B5
// Range: -1 to +1. Positive values indicate water bodies.

var ndwi = landsat8Composite.normalizedDifference(['SR_B3', 'SR_B5'])
                            .rename('NDWI');

print('NDWI range:', ndwi.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: studyArea,
  scale: 30,
  maxPixels: 1e9
}));

// --- 5d. Land Surface Temperature (LST) ---
// ST_B10 from our scaled Landsat-8 composite is already in Kelvin.
// Convert to Celsius: °C = K - 273.15

var lstKelvin  = landsat8Composite.select('ST_B10');
var lstCelsius = lstKelvin.subtract(273.15).rename('LST');
// .subtract(273.15) converts every pixel from Kelvin to Celsius.

print('LST range (°C):', lstCelsius.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: studyArea,
  scale: 30,
  maxPixels: 1e9
}));

// --- 5e. Also compute NDVI from Sentinel-2 at higher resolution (10m) ---
// Sentinel-2: NIR = B8, Red = B4
// This gives a more detailed vegetation map.

var ndviS2 = sentinel2Composite.normalizedDifference(['B8', 'B4'])
                               .rename('NDVI_S2');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 6: LAND USE / LAND COVER (LULC)                               ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// We use ESA WorldCover (10m resolution) for land cover classification.
// This dataset classifies every pixel into categories like:
//   10 = Tree cover, 20 = Shrubland, 30 = Grassland, 40 = Cropland,
//   50 = Built-up, 60 = Bare/sparse, 70 = Snow/ice,
//   80 = Permanent water, 90 = Herbaceous wetland,
//   95 = Mangroves, 100 = Moss/lichen

var lulc = ee.ImageCollection('ESA/WorldCover/v200')
  .first()             // Only one global mosaic in this collection
  .clip(studyArea)     // Clip to our study area
  .rename('LULC');     // Rename for clarity

print('LULC loaded. Classes: 10=Trees, 20=Shrub, 30=Grass, 40=Crop, '
    + '50=Built-up, 60=Bare, 80=Water');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 7: ERA5-LAND WEATHER DATA                                      ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// ERA5-Land provides global weather reanalysis data at ~11 km resolution.
// Available in GEE as hourly data. We compute the MEAN over our date range.
//
// Variables we extract:
//   1. Air Temperature (2m above ground) — in Kelvin, convert to Celsius
//   2. Relative Humidity — calculated from air temp and dewpoint temp
//   3. Wind Speed — calculated from U and V wind components
//   4. Surface Solar Radiation — total incoming solar energy

// --- 7a. Load ERA5-Land for our date range and area ---
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
  .filterBounds(studyArea)
  .filterDate(START_DATE, END_DATE);

print('ERA5-Land hourly records found:', era5.size());

// --- 7b. Air Temperature ---
// Band: 'temperature_2m' (temperature at 2 meters above ground, in Kelvin)
// Convert to Celsius and take the mean over the time period.

var airTempK = era5.select('temperature_2m').mean();
var airTempC = airTempK.subtract(273.15)
                       .clip(studyArea)
                       .rename('AirTemperature');

// --- 7c. Relative Humidity ---
// ERA5 does not provide humidity directly. We calculate it from:
//   - temperature_2m (air temperature, K)
//   - dewpoint_temperature_2m (dewpoint temperature, K)
//
// Formula (Magnus formula approximation):
//   RH = 100 × exp[(17.625 × Td) / (243.04 + Td)]
//                / exp[(17.625 × T)  / (243.04 + T)]
// where T and Td are in Celsius.

// First, get mean values in Kelvin, then convert to Celsius.
var dewpointK = era5.select('dewpoint_temperature_2m').mean();
var dewpointC = dewpointK.subtract(273.15);
var airTempForRH = airTempK.subtract(273.15);

// Apply the Magnus formula step by step:
// Numerator exponent: (17.625 × Td) / (243.04 + Td)
var numerator = dewpointC.multiply(17.625).divide(dewpointC.add(243.04));
// Denominator exponent: (17.625 × T) / (243.04 + T)
var denominator = airTempForRH.multiply(17.625).divide(airTempForRH.add(243.04));

// RH = 100 × exp(numerator) / exp(denominator) = 100 × exp(numerator - denominator)
var humidity = numerator.subtract(denominator)
                        .exp()             // e^(numerator - denominator)
                        .multiply(100)     // Convert to percentage
                        .clip(studyArea)
                        .rename('Humidity');

// --- 7d. Wind Speed ---
// ERA5 provides wind as U (east-west) and V (north-south) components.
// Wind speed = sqrt(U² + V²)
// Bands: 'u_component_of_wind_10m', 'v_component_of_wind_10m' (m/s)

var windU = era5.select('u_component_of_wind_10m').mean();
var windV = era5.select('v_component_of_wind_10m').mean();

// Calculate speed using Pythagorean theorem.
var windSpeed = windU.pow(2)           // U²
                     .add(windV.pow(2)) // + V²
                     .sqrt()            // √(U² + V²)
                     .clip(studyArea)
                     .rename('WindSpeed');

// --- 7e. Surface Solar Radiation ---
// Band: 'surface_solar_radiation_downwards_hourly'
// Units: J/m² (Joules per square meter, accumulated over the hour)
// We take the mean to get average hourly solar radiation.

var solarRad = era5.select('surface_solar_radiation_downwards_hourly')
                   .mean()
                   .clip(studyArea)
                   .rename('SolarRadiation');

print('ERA5 weather data processed successfully.');
print('Air Temperature range (°C):',
  airTempC.reduceRegion({
    reducer: ee.Reducer.minMax(), geometry: studyArea,
    scale: 11132, maxPixels: 1e9
  })
);


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 8: COMBINE ALL LAYERS INTO ONE MULTI-BAND IMAGE               ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Stack all computed layers into a single image.
// This makes it easy to sample all values at once for CSV export.

// ERA5 is at coarser resolution (~11 km). We resample it to match Landsat.
// .resample('bilinear') smoothly interpolates between ERA5 pixels.
// .reproject() forces the image to our target resolution.

var airTempResampled = airTempC
  .resample('bilinear')
  .reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});

var humidityResampled = humidity
  .resample('bilinear')
  .reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});

var windSpeedResampled = windSpeed
  .resample('bilinear')
  .reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});

var solarRadResampled = solarRad
  .resample('bilinear')
  .reproject({crs: 'EPSG:4326', scale: EXPORT_SCALE});

// Combine everything into one multi-band image.
var combinedImage = lstCelsius
  .addBands(ndvi)
  .addBands(ndbi)
  .addBands(ndwi)
  .addBands(airTempResampled)
  .addBands(humidityResampled)
  .addBands(windSpeedResampled)
  .addBands(solarRadResampled);

// Print the band names to verify everything is included.
print('Combined image bands:', combinedImage.bandNames());


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 9: MAP VISUALIZATION                                           ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Add every layer to the Earth Engine map with appropriate color palettes.
// You can toggle layers on/off in the "Layers" panel on the map.

// --- 9a. True Color Composite (Landsat-8) ---
// Shows the city as it looks to the human eye.
// Red = SR_B4, Green = SR_B3, Blue = SR_B2
Map.addLayer(
  landsat8Composite,
  {bands: ['SR_B4', 'SR_B3', 'SR_B2'], min: 0, max: 0.3},
  'Landsat-8 True Color',
  false  // false = layer is off by default (click to show)
);

// --- 9b. True Color Composite (Sentinel-2) ---
// Higher resolution (10m) true color.
Map.addLayer(
  sentinel2Composite,
  {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3},
  'Sentinel-2 True Color',
  false
);

// --- 9c. Land Surface Temperature (LST) ---
// Red/yellow = hot areas (urban heat islands), Blue/green = cooler areas.
Map.addLayer(
  lstCelsius,
  {
    min: 25, max: 55,
    palette: [
      '1a3678',  // Deep blue (coolest)
      '2955bc',  // Blue
      '5699ff',  // Light blue
      '8dbae9',  // Pale blue
      'acd1ff',  // Very light blue
      'caebf2',  // Ice blue
      'e0f3db',  // Pale green
      'a8ddb5',  // Light green
      '7bccc4',  // Teal
      'f7fcb9',  // Pale yellow
      'fff7bc',  // Light yellow
      'fec44f',  // Yellow
      'fe9929',  // Orange
      'ec7014',  // Dark orange
      'cc4c02',  // Red-orange
      '993404',  // Dark red
      '662506'   // Deep brown (hottest)
    ]
  },
  'Land Surface Temperature (°C)',
  true   // true = layer is on by default
);

// --- 9d. NDVI (Vegetation) ---
// Green = dense vegetation, Brown/red = bare soil or no vegetation.
Map.addLayer(
  ndvi,
  {
    min: -0.2, max: 0.8,
    palette: ['d73027', 'f46d43', 'fdae61', 'fee08b',
              'd9ef8b', 'a6d96a', '66bd63', '1a9850', '006837']
  },
  'NDVI (Vegetation)',
  false
);

// --- 9e. NDBI (Built-up) ---
// Yellow/Red = built-up, Blue = non-built-up.
Map.addLayer(
  ndbi,
  {
    min: -0.3, max: 0.3,
    palette: ['2166ac', '67a9cf', 'd1e5f0', 'fddbc7',
              'ef8a62', 'b2182b']
  },
  'NDBI (Built-up)',
  false
);

// --- 9f. NDWI (Water) ---
// Blue = water, Brown = dry land.
Map.addLayer(
  ndwi,
  {
    min: -0.5, max: 0.5,
    palette: ['d73027', 'fc8d59', 'fee090', 'e0f3f8',
              '91bfdb', '4575b4']
  },
  'NDWI (Water)',
  false
);

// --- 9g. LULC (Land Cover) ---
// Each class has its own color (defined by ESA WorldCover).
Map.addLayer(
  lulc,
  {
    min: 10, max: 100,
    palette: [
      '006400',  // 10 = Tree cover (dark green)
      'ffbb22',  // 20 = Shrubland (orange)
      'ffff4c',  // 30 = Grassland (yellow)
      'f096ff',  // 40 = Cropland (pink)
      'fa0000',  // 50 = Built-up (red)
      'b4b4b4',  // 60 = Bare/sparse (gray)
      'f0f0f0',  // 70 = Snow/ice (white)
      '0064c8',  // 80 = Water (blue)
      '0096a0',  // 90 = Wetland (teal)
      '00cf75',  // 95 = Mangroves (green)
      'fae6a0'   // 100 = Moss/lichen (beige)
    ]
  },
  'Land Use / Land Cover',
  false
);

// --- 9h. ERA5 Weather Layers ---
Map.addLayer(
  airTempC,
  {min: 25, max: 45, palette: ['blue', 'cyan', 'yellow', 'orange', 'red']},
  'Air Temperature (°C)',
  false
);

Map.addLayer(
  humidity,
  {min: 20, max: 90, palette: ['ffffcc', 'a1dab4', '41b6c4', '225ea8']},
  'Relative Humidity (%)',
  false
);

Map.addLayer(
  windSpeed,
  {min: 0, max: 6, palette: ['ffffff', 'c6dbef', '6baed6', '2171b5', '08306b']},
  'Wind Speed (m/s)',
  false
);

Map.addLayer(
  solarRad,
  {min: 500000, max: 3500000, palette: ['f7fcf5', 'd9f0a3', 'addd8e',
   '78c679', '31a354', '006837']},
  'Solar Radiation (J/m²)',
  false
);

// --- 9i. Sentinel-2 NDVI (High Resolution) ---
Map.addLayer(
  ndviS2,
  {
    min: -0.2, max: 0.8,
    palette: ['d73027', 'f46d43', 'fdae61', 'fee08b',
              'd9ef8b', 'a6d96a', '66bd63', '1a9850', '006837']
  },
  'NDVI from Sentinel-2 (10m)',
  false
);


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 10: EXPORT GEOTIFF FILES TO GOOGLE DRIVE                      ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// Each layer is exported as a separate GeoTIFF file.
// GeoTIFF = a standard raster format that preserves geographic coordinates.
// After running, go to the "Tasks" tab and click "Run" on each export task.

// Helper function to export a single-band image as GeoTIFF.
function exportGeoTIFF(image, description, bandName) {
  Export.image.toDrive({
    image: image,                    // The image to export
    description: description,        // Task name (shown in Tasks tab)
    folder: DRIVE_FOLDER,            // Google Drive folder
    fileNamePrefix: CITY_NAME + '_' + bandName,  // File name
    region: studyArea,               // Area to export
    scale: EXPORT_SCALE,             // Pixel resolution in meters
    crs: 'EPSG:4326',               // Coordinate system (WGS84 lat/lon)
    maxPixels: 1e13,                 // Allow large exports
    fileFormat: 'GeoTIFF'            // Output format
  });
}

// Export each layer:
exportGeoTIFF(lstCelsius, 'Export_LST', 'LST');
exportGeoTIFF(ndvi,       'Export_NDVI', 'NDVI');
exportGeoTIFF(ndbi,       'Export_NDBI', 'NDBI');
exportGeoTIFF(ndwi,       'Export_NDWI', 'NDWI');
exportGeoTIFF(lulc,       'Export_LULC', 'LULC');

// Export ERA5 layers
exportGeoTIFF(airTempC,   'Export_AirTemperature', 'AirTemperature');
exportGeoTIFF(humidity,   'Export_Humidity', 'Humidity');
exportGeoTIFF(windSpeed,  'Export_WindSpeed', 'WindSpeed');
exportGeoTIFF(solarRad,   'Export_SolarRadiation', 'SolarRadiation');

// Export satellite composites (multi-band)
Export.image.toDrive({
  image: landsat8Composite.select(['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']),
  description: 'Export_Landsat8_Composite',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_Landsat8_Composite',
  region: studyArea,
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

Export.image.toDrive({
  image: sentinel2Composite.select(['B2','B3','B4','B8','B11','B12']),
  description: 'Export_Sentinel2_Composite',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_Sentinel2_Composite',
  region: studyArea,
  scale: 10,
  crs: 'EPSG:4326',
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF'
});

print('GeoTIFF export tasks created. Go to Tasks tab → click Run on each.');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 11: EXPORT CSV — PIXEL-LEVEL DATA FOR AI/ML TRAINING          ║
// ╚═══════════════════════════════════════════════════════════════════════════╝
// We sample the combined image at regular grid points to create a CSV.
// Each row in the CSV = one geographic location with all variable values.
// This CSV will be the primary input for your AI/ML model later.

// --- 11a. Generate a Grid of Sample Points ---
// Create a regular grid of points covering the study area.
// Each point is one row in the CSV.

var samplePoints = combinedImage.sample({
  region: studyArea,           // Area to sample from
  scale: CSV_SAMPLE_SCALE,     // Distance between sample points
  numPixels: MAX_CSV_POINTS,   // Maximum number of points
  seed: 42,                    // Random seed for reproducibility
  geometries: true             // Include lat/lon coordinates
});

// --- 11b. Add Latitude and Longitude as Properties ---
// The coordinates are in the geometry but we need them as columns in CSV.
samplePoints = samplePoints.map(function(feature) {
  var coords = feature.geometry().coordinates();
  // coords is a list: [longitude, latitude]
  return feature
    .set('Longitude', coords.get(0))  // First element = longitude
    .set('Latitude', coords.get(1));  // Second element = latitude
});

// --- 11c. Add LULC Class to Each Point ---
// LULC is categorical (integer), so we sample it separately and join.
var lulcSampled = lulc.sample({
  region: studyArea,
  scale: CSV_SAMPLE_SCALE,
  numPixels: MAX_CSV_POINTS,
  seed: 42,
  geometries: true
});

// Create a spatial join to attach LULC values to our sample points.
// We use a small distance threshold (same as sample scale) for matching.
var spatialFilter = ee.Filter.withinDistance({
  distance: CSV_SAMPLE_SCALE,
  leftField: '.geo',
  rightField: '.geo',
  maxError: 10
});

// Alternative simpler approach: sample LULC at the same points
var lulcAtPoints = lulc.reduceRegions({
  collection: samplePoints,
  reducer: ee.Reducer.first(),  // Get the LULC value at each point
  scale: CSV_SAMPLE_SCALE
});

// Rename the 'first' property to 'LULC'
lulcAtPoints = lulcAtPoints.map(function(feature) {
  return feature.set('LULC', feature.get('first'));
});

// --- 11d. Select Only the Columns We Want ---
var csvData = lulcAtPoints.select({
  propertyNames: [
    'Latitude',
    'Longitude',
    'LST',
    'NDVI',
    'NDBI',
    'NDWI',
    'AirTemperature',
    'Humidity',
    'WindSpeed',
    'SolarRadiation',
    'LULC'
  ],
  retainGeometry: false  // Don't include geometry column in CSV
});

// Print sample size and a preview
print('Total sample points for CSV:', csvData.size());
print('CSV preview (first 5 rows):', csvData.limit(5));

// --- 11e. Export to CSV ---
Export.table.toDrive({
  collection: csvData,
  description: 'Export_Training_CSV',
  folder: DRIVE_FOLDER,
  fileNamePrefix: CITY_NAME + '_UHI_Training_Data',
  fileFormat: 'CSV'
});

print('CSV export task created. Go to Tasks tab → click Run.');


// ╔═══════════════════════════════════════════════════════════════════════════╗
// ║  SECTION 12: PRINT SUMMARY AND METADATA                                ║
// ╚═══════════════════════════════════════════════════════════════════════════╝

print('═══════════════════════════════════════════════');
print('PIPELINE EXECUTION COMPLETE');
print('═══════════════════════════════════════════════');
print('City:', CITY_NAME);
print('Date Range:', START_DATE, 'to', END_DATE);
print('Export Scale:', EXPORT_SCALE, 'meters');
print('Export Folder:', DRIVE_FOLDER);
print('');
print('NEXT STEPS:');
print('1. Check the Tasks tab (top-right corner)');
print('2. Click "Run" on each export task');
print('3. Files will appear in your Google Drive →', DRIVE_FOLDER);
print('4. Download the CSV file for AI/ML training');
print('═══════════════════════════════════════════════');
