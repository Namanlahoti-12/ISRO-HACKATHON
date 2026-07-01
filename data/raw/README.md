# Raw Data

This directory stores raw data files downloaded from Google Earth Engine.

## Expected Contents
After running the GEE pipeline and exporting to Google Drive, download files here:

- `{City}_Landsat_Composite.tif` — Landsat-8/9 multi-band surface reflectance
- `{City}_Sentinel2_Composite.tif` — Sentinel-2 multi-band surface reflectance
- Individual GeoTIFF layers (LST, NDVI, NDBI, etc.)

## Notes
- Do NOT modify raw files. Process them into `../intermediate/` or `../processed/`.
- Keep original filenames from Google Drive exports.
