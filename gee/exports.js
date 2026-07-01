// ============================================================================
// MODULE: exports.js — Centralized Export Functions
// ============================================================================
// Provides reusable export functions for GeoTIFF and CSV formats.
// All exports use consistent CRS, scale, and folder settings.
// ============================================================================

// ─── Export Single-Band GeoTIFF ─────────────────────────────────────────────
function exportGeoTIFF(image, description, bandName, studyArea, config) {
  Export.image.toDrive({
    image: image,
    description: description,
    folder: config.DRIVE_FOLDER,
    fileNamePrefix: config.CITY_NAME + '_' + bandName,
    region: studyArea,
    scale: config.EXPORT_SCALE,
    crs: config.EXPORT_CRS,
    maxPixels: config.MAX_PIXELS,
    fileFormat: 'GeoTIFF'
  });
}

// ─── Export Multi-Band GeoTIFF ──────────────────────────────────────────────
function exportMultiBandGeoTIFF(image, description, bandName, studyArea, config, scale) {
  Export.image.toDrive({
    image: image,
    description: description,
    folder: config.DRIVE_FOLDER,
    fileNamePrefix: config.CITY_NAME + '_' + bandName,
    region: studyArea,
    scale: scale || config.EXPORT_SCALE,
    crs: config.EXPORT_CRS,
    maxPixels: config.MAX_PIXELS,
    fileFormat: 'GeoTIFF'
  });
}

// ─── Export FeatureCollection as CSV ─────────────────────────────────────────
function exportCSV(featureCollection, description, fileName, config) {
  Export.table.toDrive({
    collection: featureCollection,
    description: description,
    folder: config.DRIVE_FOLDER,
    fileNamePrefix: config.CITY_NAME + '_' + fileName,
    fileFormat: 'CSV'
  });
}

// ─── Batch Export Helper ────────────────────────────────────────────────────
// Exports a dictionary of {name: image} pairs as individual GeoTIFFs.
function batchExportGeoTIFF(imageDictionary, studyArea, config) {
  var names = Object.keys(imageDictionary);
  for (var i = 0; i < names.length; i++) {
    var name = names[i];
    exportGeoTIFF(
      imageDictionary[name],
      'Export_' + name,
      name,
      studyArea,
      config
    );
  }
}
