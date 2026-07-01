// ============================================================================
// MODULE: ndvi.js — Normalized Difference Vegetation Index
// ============================================================================
// NDVI = (NIR − Red) / (NIR + Red)
//
// Measures vegetation health and density.
//   -1 to 0   → Water, bare soil, clouds
//   0 to 0.2  → Bare soil, rock, sand
//   0.2 to 0.4 → Sparse vegetation, shrubs
//   0.4 to 0.6 → Moderate vegetation
//   0.6 to 1.0 → Dense, healthy vegetation
//
// Band mapping:
//   Landsat-8/9:  NIR = SR_B5, Red = SR_B4
//   Sentinel-2:   NIR = B8,    Red = B4
//
// Reference: Tucker (1979), Rouse et al. (1974)
// ============================================================================

function computeNDVI_Landsat(landsatComposite) {
  return landsatComposite.normalizedDifference(['SR_B5', 'SR_B4'])
    .rename('NDVI');
}

function computeNDVI_S2(sentinel2Composite) {
  return sentinel2Composite.normalizedDifference(['B8', 'B4'])
    .rename('NDVI_S2');
}
