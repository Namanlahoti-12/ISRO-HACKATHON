// ============================================================================
// MODULE: lst.js — Land Surface Temperature
// ============================================================================
// Computes LST from Landsat-8/9 Collection 2 Level 2 Surface Temperature.
//
// The L2 ST_B10 product is already atmospherically corrected and includes
// emissivity correction using ASTER GED (Global Emissivity Database).
// This is the USGS-recommended approach.
//
// We convert from Kelvin to Celsius and compute derived heat indices:
//   - UHII (Urban Heat Island Intensity) = LST_pixel − LST_rural_mean
//   - UTFVI (Urban Thermal Field Variance Index) = (LST − LST_mean) / LST_mean
//
// References:
//   - USGS Landsat C2 L2 Science Product Guide
//   - Sobrino et al. (2004) for NDVI-based emissivity (alternative method)
//   - Guha et al. (2018) for UTFVI methodology
// ============================================================================

// ─── Extract LST from Landsat Composite ─────────────────────────────────────
// Input: scaled Landsat composite (ST_B10 already in Kelvin)
// Output: single-band image in Celsius

function computeLST(landsatComposite) {
  return landsatComposite.select('ST_B10')
    .subtract(273.15)
    .clamp(-10, 70)      // Valid range for Indian cities
    .rename('LST');
}

// ─── UHI Intensity ──────────────────────────────────────────────────────────
// UHII = LST_pixel − mean LST of rural/non-urban pixels.
// "Rural" is defined as pixels where LULC ≠ built-up (WorldCover class ≠ 50).
// Positive UHII = hotter than rural surroundings = heat island.

function computeUHII(lstImage, lulcImage, studyArea) {
  // Create rural mask: everything except built-up (class 50)
  var ruralMask = lulcImage.neq(50);
  var ruralLST = lstImage.updateMask(ruralMask);

  // Mean LST of rural pixels in the study area
  var ruralMeanDict = ruralLST.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: studyArea,
    scale: 30,
    maxPixels: 1e9
  });
  var ruralMean = ee.Number(ruralMeanDict.get('LST'));

  // UHII = LST - rural mean
  return lstImage.subtract(ruralMean).rename('UHI_Intensity');
}

// ─── UTFVI (Urban Thermal Field Variance Index) ────────────────────────────
// UTFVI = (LST − LST_mean) / LST_mean
// Quantifies how much a pixel deviates from the area mean temperature.
// Categories (Guha et al., 2018):
//   UTFVI < 0     → None (ecological quality: Excellent)
//   0–0.005       → Weak (Good)
//   0.005–0.010   → Moderate (Normal)
//   0.010–0.015   → Strong (Bad)
//   0.015–0.020   → Stronger (Worse)
//   > 0.020       → Strongest (Worst)

function computeUTFVI(lstImage, studyArea) {
  var meanDict = lstImage.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: studyArea,
    scale: 30,
    maxPixels: 1e9
  });
  var lstMean = ee.Number(meanDict.get('LST'));

  return lstImage.subtract(lstMean)
    .divide(lstMean)
    .rename('UTFVI');
}
