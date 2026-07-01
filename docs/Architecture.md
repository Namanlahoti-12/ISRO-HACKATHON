# System Architecture

Technical architecture of the Urban Heat AI system.

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph GEE["Google Earth Engine (Cloud)"]
        direction TB
        M["main.js\nComplete Pipeline"]
        M --> SAT["Satellite Processing\nLandsat-8/9 + Sentinel-2"]
        M --> WX["Weather Processing\nERA5-Land"]
        M --> ANC["Ancillary Data\nGHSL, VIIRS, WorldPop,\nSRTM, WorldCover, etc."]
        SAT --> FE["Feature Engineering\n37+ features"]
        WX --> FE
        ANC --> FE
        FE --> EXP["Export Engine"]
        EXP --> TIFF["GeoTIFFs → Google Drive"]
        EXP --> CSV["Master CSV → Google Drive"]
    end

    subgraph LOCAL["Local Machine"]
        direction TB
        DRIVE["Google Drive\n(Download)"] --> DATA["data/ directory"]
        DATA --> VALID["utils/data_validator.py\nValidation + Cleaning"]
        VALID --> ML["ML Training\n(pandas, sklearn, xgboost)"]
        ML --> MODEL["Trained Model\nmodels/"]
        MODEL --> PRED["Predictions\noutputs/"]
    end

    TIFF --> DRIVE
    CSV --> DRIVE
```

---

## Module Dependency Graph

```mermaid
flowchart TD
    CONFIG["config.js\n(All Parameters)"] --> CLOUD["cloudMask.js"]
    CONFIG --> EXPORT["exports.js"]
    
    CLOUD --> L8["Landsat-8/9\nProcessing"]
    CLOUD --> S2["Sentinel-2\nProcessing"]
    
    L8 --> LST["lst.js\nLST, UHII, UTFVI"]
    L8 --> NDVI["ndvi.js"]
    L8 --> NDBI["ndbi.js"]
    L8 --> NDWI["ndwi.js"]
    L8 --> MNDWI["mndwi.js"]
    L8 --> MORPH_ALB["morphology.js\n(Albedo)"]
    
    S2 --> NDVI
    
    NDVI --> MORPH_DIST["morphology.js\n(Distances, Densities)"]
    NDWI --> MORPH_DIST
    
    CONFIG --> WX["weather.js\n(ERA5)"]
    CONFIG --> LULC["lulc.js\n(WorldCover, DW, GAIA)"]
    CONFIG --> MORPH_TERRAIN["morphology.js\n(SRTM Terrain)"]
    CONFIG --> POP["population.js\n(WorldPop, GHSL)"]
    
    LST & NDVI & NDBI & NDWI & MNDWI --> COMBINE["Master Image"]
    WX & LULC & MORPH_ALB & MORPH_DIST & MORPH_TERRAIN & POP --> COMBINE
    
    COMBINE --> EXPORT
```

---

## Design Principles

### 1. Single Runnable Script
GEE Code Editor does not support JavaScript module imports from local files. Therefore, `main.js` is a self-contained script that includes all logic from the module files. The module files (`config.js`, `cloudMask.js`, etc.) exist as **organized reference documentation** — each file shows the isolated logic for one concern.

### 2. Modular Sections
`main.js` is organized into 17 clearly labeled sections with visual separators. This allows:
- Easy navigation (search for "SECTION 7" to find ERA5 weather)
- Independent modification of any section without affecting others
- Future refactoring into GEE repository modules using `require()`

### 3. Configuration-Driven
All user-editable parameters are in Section 1. To analyze a different city, the user only changes ~5 variables. No other code modifications needed.

### 4. Resolution Alignment
Different datasets have different native resolutions (10m to 11km). The pipeline:
- Processes each dataset at its native resolution
- Resamples to the export resolution (30m) only at the final stacking step
- Uses bilinear interpolation for continuous variables
- Uses nearest-neighbor for categorical variables (LULC classes)

### 5. Defensive Data Handling
- Reflectance clamped to [0, 1]
- LST clamped to [-10, 70]°C
- Humidity clamped to [0, 100]%
- Nighttime lights floored at 0 (removes negative artifacts)
- try/catch for optional datasets (GHSL)
- QualityScore tracks observation count per pixel

### 6. ML-Ready Output
The CSV is designed for direct ingestion by ML frameworks:
- No geometry columns (retainGeometry: false)
- Consistent column naming (snake_case + PascalCase)
- No missing values (masked pixels excluded during sampling)
- Explicit target variable (LST)
- Metadata columns (PixelID, Timestamp) for tracking

---

## Extension Points

### Adding New Features
1. Compute the new feature as an `ee.Image` in the appropriate section
2. Add it to the `masterImage` stack in Section 13
3. Add the band name to the `csvColumns` array in Section 16
4. Add an `exportTIFF()` call in Section 15
5. Add a `Map.addLayer()` call in Section 14

### Adding ML (Future)
The CSV output is compatible with:
```python
import pandas as pd
df = pd.read_csv('Delhi_UHI_MasterDataset.csv')
X = df.drop(columns=['PixelID','Latitude','Longitude','Timestamp','LST'])
y = df['LST']
```

### Migrating to GEE Repository Modules
When you have a GEE repository, convert module files to:
```javascript
// In your GEE repo: users/yourname/UrbanHeatAI:modules/cloudMask
exports.maskLandsatClouds = function(image) { ... };
exports.scaleLandsat = function(image) { ... };

// In main.js:
var cloudMask = require('users/yourname/UrbanHeatAI:modules/cloudMask');
```

---

## Performance Considerations

| Operation | Cost | Optimization |
|-----------|------|-------------|
| ERA5 hourly filtering | High (many images) | Consider using MONTHLY_AGGR instead |
| fastDistanceTransform | High (global search) | Limited to 512 pixel radius |
| reduceNeighborhood | Moderate | Fixed kernel radius of 5 pixels |
| reproject + resample | Moderate | Applied only once at final stacking |
| CSV sampling | High for large areas | Limited by MAX_CSV_POINTS |
| GeoTIFF export | Low per file | 33 parallel tasks |
