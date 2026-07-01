// ============================================================================
// MODULE: ndwi.js — Normalized Difference Water Index
// ============================================================================
// NDWI = (Green − NIR) / (Green + NIR)
//
// Detects open water bodies and moisture content.
//   Positive values → Water surfaces
//   Negative values → Dry land, vegetation
//
// Band mapping:
//   Landsat-8/9:  Green = SR_B3, NIR = SR_B5
//   Sentinel-2:   Green = B3,    NIR = B8
//
// Reference: McFeeters (1996)
// ============================================================================

function computeNDWI_Landsat(landsatComposite) {
  return landsatComposite.normalizedDifference(['SR_B3', 'SR_B5'])
    .rename('NDWI');
}

function computeNDWI_S2(sentinel2Composite) {
  return sentinel2Composite.normalizedDifference(['B3', 'B8'])
    .rename('NDWI_S2');
}
