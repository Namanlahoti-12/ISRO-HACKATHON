// ============================================================================
// MODULE: population.js — Population Density
// ============================================================================
// Provides gridded population density from two global datasets:
//
// 1. WorldPop (100m resolution)
//    UN-adjusted population count per grid cell, available annually.
//    Best for high-resolution urban population mapping.
//
// 2. GHSL Population (GHS-POP, 100m/1km)
//    Disaggregated population using built-up land as a proxy.
//    Consistent methodology across epochs (1975–2030).
//
// We use WorldPop as the primary source (higher spatial accuracy for India)
// and GHSL as a complementary estimate.
//
// References:
//   - Tatem (2017) for WorldPop
//   - Schiavina et al. (2023) for GHSL POP
// ============================================================================

function loadWorldPop(studyArea, year) {
  // WorldPop UN-adjusted 100m population.
  // Filter to the requested year and India (IND).
  var pop = ee.ImageCollection('WorldPop/GP/100m/pop')
    .filterDate(String(year) + '-01-01', String(year) + '-12-31')
    .filter(ee.Filter.eq('country', 'IND'))
    .mosaic()
    .clip(studyArea)
    .rename('Population_Density');

  return pop;
}

function loadGHSLPop(studyArea) {
  // GHSL Population for the most recent epoch.
  var ghslPop = ee.ImageCollection('JRC/GHSL/P2023A/GHS_POP')
    .filterDate('2018-01-01', '2023-12-31')
    .mosaic()
    .clip(studyArea);

  return ghslPop.select(0).rename('Population_GHSL');
}

// ─── Anthropogenic Heat Proxy ───────────────────────────────────────────────
// No direct anthropogenic heat data exists in GEE.
// We estimate it as: Nighttime Lights × Population Density (normalized).
// Scientific basis: Both light emissions and population density correlate
// strongly with waste heat from buildings, vehicles, and industry.
// Reference: Chen et al. (2014), Dong et al. (2017)

function computeAnthropogenicHeat(nighttimeLights, populationDensity) {
  // Normalize both layers to 0–1 range, then multiply.
  var ntlNorm = nighttimeLights.unitScale(0, 100);   // Rough scale
  var popNorm = populationDensity.unitScale(0, 10000); // Rough scale
  return ntlNorm.multiply(popNorm).rename('Anthropogenic_Heat');
}
