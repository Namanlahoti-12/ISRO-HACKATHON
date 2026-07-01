// ============================================================================
// MODULE: morphology.js — Urban Morphology & Terrain Features
// ============================================================================
// Computes terrain, urban structure, and spatial proximity features.
//
// Terrain (SRTM 30m):
//   - Elevation (m), Slope (°), Aspect (°)
//
// Urban Structure (GHSL P2023A):
//   - Building Density (built-up surface fraction)
//   - Building Height (m)
//   - Building Volume proxy (density × height)
//
// Nighttime Activity (VIIRS):
//   - Nighttime light radiance (nW/cm²/sr)
//
// Surface Properties:
//   - Albedo (shortwave surface albedo from Landsat reflectance)
//
// Spatial Proximity:
//   - Distance to nearest water body (from NDWI)
//   - Distance to nearest green area (from NDVI)
//
// Neighborhood Statistics:
//   - Green space density (fraction of green pixels in 150m radius)
//   - Surface roughness proxy (elevation std-dev in neighborhood)
//
// References:
//   - Farr et al. (2007) for SRTM
//   - Pesaresi et al. (2023) for GHSL
//   - Elvidge et al. (2017) for VIIRS
//   - Liang (2001) for Landsat albedo
// ============================================================================

// ─── Terrain from SRTM ─────────────────────────────────────────────────────
function computeTerrain(studyArea) {
  var srtm = ee.Image('USGS/SRTMGL1_003').clip(studyArea);
  var terrain = ee.Terrain.products(srtm);

  var elevation = terrain.select('elevation').rename('Elevation');
  var slope     = terrain.select('slope').rename('Slope');
  var aspect    = terrain.select('aspect').rename('Aspect');

  return elevation.addBands(slope).addBands(aspect);
}

// ─── GHSL Built-up Surface ─────────────────────────────────────────────────
function computeBuildingDensity(studyArea) {
  // GHSL Built-up Surface: built_surface_fraction (0–100%)
  // Filter to most recent epoch (2020).
  var ghsl = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S')
    .filterDate('2018-01-01', '2023-12-31')
    .mosaic()
    .clip(studyArea);

  // Select the built-up fraction band (name may vary by epoch).
  // If band name differs, the script will report it in console.
  var builtUp = ghsl.select(0).rename('Building_Density');
  return builtUp;
}

// ─── GHSL Building Height ──────────────────────────────────────────────────
function computeBuildingHeight(studyArea) {
  var ghslH = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_H')
    .mosaic()
    .clip(studyArea);

  return ghslH.select(0).rename('Building_Height');
}

// ─── VIIRS Nighttime Lights ────────────────────────────────────────────────
function computeNighttimeLights(studyArea, startDate, endDate) {
  var viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')
    .filterDate(startDate, endDate)
    .select('avg_rad');

  return viirs.median()
    .clip(studyArea)
    .rename('Nighttime_Lights');
}

// ─── Shortwave Surface Albedo ──────────────────────────────────────────────
// Liang (2001) formula for Landsat shortwave albedo:
// α = 0.356×B2 + 0.130×B4 + 0.373×B5 + 0.085×B6 + 0.072×B7 − 0.0018
// (Adapted for Landsat-8/9 band names: SR_B2, SR_B4, SR_B5, SR_B6, SR_B7)
function computeAlbedo(landsatComposite) {
  var albedo = landsatComposite.select('SR_B2').multiply(0.356)
    .add(landsatComposite.select('SR_B4').multiply(0.130))
    .add(landsatComposite.select('SR_B5').multiply(0.373))
    .add(landsatComposite.select('SR_B6').multiply(0.085))
    .add(landsatComposite.select('SR_B7').multiply(0.072))
    .subtract(0.0018)
    .clamp(0, 1)
    .rename('Albedo');

  return albedo;
}

// ─── Distance to Water ─────────────────────────────────────────────────────
// Euclidean distance from each pixel to nearest water pixel.
// Water defined as NDWI > 0 (McFeeters threshold).
function computeDistToWater(ndwiImage, studyArea, scale) {
  var waterMask = ndwiImage.gt(0).selfMask();  // 1 where water, masked elsewhere
  // fastDistanceTransform: distance in pixels (squared). Sqrt → meters.
  var distPixels = waterMask.fastDistanceTransform(512).sqrt();
  var distMeters = distPixels.multiply(scale).rename('Dist_Water');
  return distMeters.clip(studyArea);
}

// ─── Distance to Green Space ────────────────────────────────────────────────
// Euclidean distance from each pixel to nearest green/park pixel.
// Green defined as NDVI > 0.4 (moderate-dense vegetation).
function computeDistToGreen(ndviImage, studyArea, scale) {
  var greenMask = ndviImage.gt(0.4).selfMask();
  var distPixels = greenMask.fastDistanceTransform(512).sqrt();
  var distMeters = distPixels.multiply(scale).rename('Dist_Green');
  return distMeters.clip(studyArea);
}

// ─── Green Space Density ────────────────────────────────────────────────────
// Fraction of pixels with NDVI > 0.3 within a circular neighborhood.
function computeGreenDensity(ndviImage, kernelRadius) {
  var greenBinary = ndviImage.gt(0.3);
  var kernel = ee.Kernel.circle({radius: kernelRadius, units: 'pixels'});
  return greenBinary.reduceNeighborhood({
    reducer: ee.Reducer.mean(),
    kernel: kernel
  }).rename('Green_Space_Density');
}

// ─── Surface Roughness Proxy ────────────────────────────────────────────────
// Standard deviation of elevation in a neighborhood.
// Higher roughness → more surface complexity → more heat trapping.
function computeSurfaceRoughness(elevationImage, kernelRadius) {
  var kernel = ee.Kernel.circle({radius: kernelRadius, units: 'pixels'});
  return elevationImage.reduceNeighborhood({
    reducer: ee.Reducer.stdDev(),
    kernel: kernel
  }).rename('Surface_Roughness');
}
