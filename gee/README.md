# GEE Scripts — Module Reference

This directory contains the Google Earth Engine JavaScript pipeline.

## How It Works

> **Only `main.js` is runnable.** The other `.js` files are reference modules that document the logic for each concern separately. Since GEE Code Editor does not support local file imports, everything is consolidated into `main.js`.

## Files

| File | Purpose | Runnable? |
|------|---------|-----------|
| **`main.js`** | **Complete pipeline — copy into GEE Code Editor** | **YES** |
| `config.js` | Configuration reference (cities, dates, thresholds) | Reference |
| `cloudMask.js` | Cloud masking functions (Landsat QA_PIXEL + S2 QA60) | Reference |
| `lst.js` | Land Surface Temperature + UHI Intensity + UTFVI | Reference |
| `ndvi.js` | Vegetation index (Landsat + Sentinel-2) | Reference |
| `ndbi.js` | Built-up index | Reference |
| `ndwi.js` | Water index | Reference |
| `mndwi.js` | Modified water index (urban-optimized) | Reference |
| `lulc.js` | Land cover (ESA WorldCover, Dynamic World, GAIA, Hansen) | Reference |
| `weather.js` | ERA5-Land weather (8 variables) | Reference |
| `morphology.js` | Terrain, buildings, lights, albedo, distances, densities | Reference |
| `population.js` | WorldPop + GHSL population + anthropogenic heat | Reference |
| `exports.js` | Centralized GeoTIFF and CSV export utilities | Reference |
| `legacy_v1.js` | Archived original v1 script (835 lines) | Archive |

## Quick Start

1. Open [Google Earth Engine Code Editor](https://code.earthengine.google.com)
2. Create a new script (File → New)
3. Copy the entire contents of **`main.js`** into the editor
4. Edit Section 1 (lines 30–60) for your target city
5. Click **Run**
6. Go to Tasks tab → click **Run** on each export task

## For GEE Repository Users

If you have a GEE repository, you can convert the reference modules to proper imports:

```javascript
// In your GEE repo: users/yourname/UrbanHeatAI:modules/cloudMask
exports.maskLandsatClouds = function(image) { /* ... */ };

// In main.js:
var cloudMask = require('users/yourname/UrbanHeatAI:modules/cloudMask');
var cleanImage = cloudMask.maskLandsatClouds(rawImage);
```
