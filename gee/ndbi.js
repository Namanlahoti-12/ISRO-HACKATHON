// ============================================================================
// MODULE: ndbi.js — Normalized Difference Built-up Index
// ============================================================================
// NDBI = (SWIR1 − NIR) / (SWIR1 + NIR)
//
// Highlights impervious/built-up surfaces (concrete, asphalt, rooftops).
//   Positive values → Built-up areas
//   Negative values → Vegetation or water
//
// Band mapping:
//   Landsat-8/9:  SWIR1 = SR_B6, NIR = SR_B5
//   Sentinel-2:   SWIR1 = B11,   NIR = B8
//
// Reference: Zha et al. (2003)
// ============================================================================

function computeNDBI_Landsat(landsatComposite) {
  return landsatComposite.normalizedDifference(['SR_B6', 'SR_B5'])
    .rename('NDBI');
}

function computeNDBI_S2(sentinel2Composite) {
  return sentinel2Composite.normalizedDifference(['B11', 'B8'])
    .rename('NDBI_S2');
}
