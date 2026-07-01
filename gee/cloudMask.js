// ============================================================================
// MODULE: cloudMask.js — Cloud & Shadow Masking Functions
// ============================================================================
// Provides cloud masking for Landsat-8/9 and Sentinel-2.
// Uses QA bit-flags and Sentinel-2 Cloud Probability for robust masking.
//
// References:
//   - USGS Landsat Collection 2 QA Band: https://www.usgs.gov/landsat-missions
//   - Sentinel-2 Cloud Masking: https://developers.google.com/earth-engine
// ============================================================================

// ─── Landsat-8/9 Cloud Masking ──────────────────────────────────────────────
// QA_PIXEL bit flags (Collection 2):
//   Bit 1 = Dilated Cloud    (expanded cloud boundary)
//   Bit 2 = Cirrus           (high thin clouds)
//   Bit 3 = Cloud Shadow
//   Bit 4 = Cloud
//   Bit 5 = Snow
// We mask: Cloud, Cloud Shadow, Cirrus, and Dilated Cloud.

function maskLandsatClouds(image) {
  var qa = image.select('QA_PIXEL');

  // Create bitmask for all problematic pixels.
  var dilatedCloudBit = 1 << 1;  // Bit 1
  var cirrusBit       = 1 << 2;  // Bit 2
  var cloudShadowBit  = 1 << 3;  // Bit 3
  var cloudBit        = 1 << 4;  // Bit 4

  // Pixel is clear only if ALL these bits are 0.
  var clearMask = qa.bitwiseAnd(dilatedCloudBit).eq(0)
    .and(qa.bitwiseAnd(cirrusBit).eq(0))
    .and(qa.bitwiseAnd(cloudShadowBit).eq(0))
    .and(qa.bitwiseAnd(cloudBit).eq(0));

  // Also mask pixels with saturated reflectance (invalid data).
  var saturationMask = image.select('QA_RADSAT').eq(0);

  return image.updateMask(clearMask).updateMask(saturationMask);
}

// ─── Landsat Scaling ────────────────────────────────────────────────────────
// Collection 2 Level 2 uses integer storage with scale/offset:
//   Surface Reflectance: value × 0.0000275 + (−0.2)
//   Surface Temperature: value × 0.00341802 + 149.0 → Kelvin

function scaleLandsat(image) {
  var optical = image.select('SR_B.*')
    .multiply(0.0000275).add(-0.2)
    .clamp(0, 1);  // Reflectance must be 0–1

  var thermal = image.select('ST_B10')
    .multiply(0.00341802).add(149.0);

  return image.addBands(optical, null, true)
              .addBands(thermal, null, true);
}

// ─── Sentinel-2 Cloud Masking ───────────────────────────────────────────────
// Uses QA60 band for basic cloud/cirrus detection.
// For production use, combine with S2 Cloud Probability.

function maskS2Clouds(image) {
  var qa = image.select('QA60');
  var opaqueBit = 1 << 10;
  var cirrusBit = 1 << 11;

  var clearMask = qa.bitwiseAnd(opaqueBit).eq(0)
    .and(qa.bitwiseAnd(cirrusBit).eq(0));

  return image.updateMask(clearMask);
}

// ─── Enhanced S2 Cloud Masking with Cloud Probability ───────────────────────
// Uses the COPERNICUS/S2_CLOUD_PROBABILITY dataset (s2cloudless algorithm).
// This gives a per-pixel cloud probability score (0–100%).
// More accurate than QA60 alone, especially at cloud edges.

function maskS2CloudProbability(image, cloudProbCollection) {
  // Find the matching cloud probability image by system:index.
  var cloudProb = cloudProbCollection
    .filter(ee.Filter.eq('system:index', image.get('system:index')))
    .first()
    .select('probability');

  // Mask pixels with > 40% cloud probability (adjustable threshold).
  var cloudMask = cloudProb.lt(40);

  return image.updateMask(cloudMask);
}

// ─── Sentinel-2 Scaling ─────────────────────────────────────────────────────
// SR values stored as integers × 10000. Divide to get 0–1 reflectance.

function scaleS2(image) {
  var scaled = image.select(['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'])
    .divide(10000)
    .clamp(0, 1);

  return image.addBands(scaled, null, true);
}
