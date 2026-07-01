// ============================================================================
// MODULE: lulc.js — Land Use / Land Cover
// ============================================================================
// Provides three LULC sources plus derived fractional metrics:
//
// 1. ESA WorldCover v200 (10m, 2021)
//    Global land cover with 11 classes. Most widely cited.
//    Classes: 10=Trees, 20=Shrub, 30=Grass, 40=Crop, 50=Built-up,
//             60=Bare, 70=Snow, 80=Water, 90=Wetland, 95=Mangroves, 100=Moss
//
// 2. Google Dynamic World (10m, near real-time)
//    Deep learning-based per-pixel probabilities for 9 classes.
//    Provides temporal context (seasonal land cover changes).
//
// 3. GAIA Impervious Surface (30m, annual)
//    Binary impervious surface mapping from Tsinghua University.
//    Useful for computing impervious surface fraction.
//
// 4. Hansen Global Forest Change (30m)
//    Tree cover percentage in year 2000 + annual loss/gain.
//
// References:
//   - Zanaga et al. (2022) for ESA WorldCover
//   - Brown et al. (2022) for Dynamic World
//   - Gong et al. (2020) for GAIA
//   - Hansen et al. (2013) for Global Forest Change
// ============================================================================

function loadWorldCover(studyArea) {
  return ee.ImageCollection('ESA/WorldCover/v200')
    .first()
    .clip(studyArea)
    .rename('LULC_ESA');
}

function loadDynamicWorld(studyArea, startDate, endDate) {
  // Dynamic World provides per-pixel class probabilities.
  // We take the mode (most frequent class) over our date range.
  var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
    .filterBounds(studyArea)
    .filterDate(startDate, endDate)
    .select('label');

  return dw.reduce(ee.Reducer.mode())
    .clip(studyArea)
    .rename('LULC_DW');
}

function loadGAIA(studyArea) {
  // GAIA provides impervious surface fraction (0 or 1 per pixel per year).
  // We use the most recent year available.
  return ee.Image('Tsinghua/FROM-GLC/GAIA/v10')
    .select('change_year_index')
    .gt(0)  // Any year mapped as impervious → 1
    .clip(studyArea)
    .rename('Impervious_Frac');
}

function loadTreeCover(studyArea) {
  // Hansen tree cover in year 2000 (0–100%).
  return ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
    .select('treecover2000')
    .clip(studyArea)
    .rename('Tree_Cover_Pct');
}
