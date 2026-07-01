// ============================================================================
// MODULE: mndwi.js — Modified Normalized Difference Water Index
// ============================================================================
// MNDWI = (Green − SWIR1) / (Green + SWIR1)
//
// Superior to NDWI for urban water detection because SWIR suppresses
// built-up surface noise that can cause false positives in NDWI.
//
// Band mapping:
//   Landsat-8/9:  Green = SR_B3, SWIR1 = SR_B6
//   Sentinel-2:   Green = B3,    SWIR1 = B11
//
// Reference: Xu (2006)
// ============================================================================

function computeMNDWI_Landsat(landsatComposite) {
  return landsatComposite.normalizedDifference(['SR_B3', 'SR_B6'])
    .rename('MNDWI');
}

function computeMNDWI_S2(sentinel2Composite) {
  return sentinel2Composite.normalizedDifference(['B3', 'B11'])
    .rename('MNDWI_S2');
}
