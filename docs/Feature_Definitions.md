# Feature Definitions — Data Dictionary

Complete reference for every feature in the master dataset CSV.

---

## Metadata Fields

| Feature | Type | Units | Description |
|---------|------|-------|-------------|
| `PixelID` | Integer | — | Sequential identifier for each sampled pixel |
| `Latitude` | Float | degrees | WGS84 latitude (Y coordinate) |
| `Longitude` | Float | degrees | WGS84 longitude (X coordinate) |
| `Timestamp` | String | — | Date range of the composite period |

---

## Target Variable

| Feature | Type | Units | Valid Range | Source | Formula |
|---------|------|-------|-------------|--------|---------|
| `LST` | Float | °C | −10 to 70 | Landsat-8/9 ST_B10 | Kelvin − 273.15 |

**Description**: Land Surface Temperature — the radiative temperature of the Earth's surface. This is the primary variable to predict in UHI analysis. Higher LST indicates urban heat islands.

---

## Spectral Indices

| Feature | Type | Units | Valid Range | Source | Formula | Reference |
|---------|------|-------|-------------|--------|---------|-----------|
| `NDVI` | Float | dimensionless | −1 to 1 | Landsat-8/9 | (B5−B4)/(B5+B4) | Tucker (1979) |
| `NDBI` | Float | dimensionless | −1 to 1 | Landsat-8/9 | (B6−B5)/(B6+B5) | Zha et al. (2003) |
| `NDWI` | Float | dimensionless | −1 to 1 | Landsat-8/9 | (B3−B5)/(B3+B5) | McFeeters (1996) |
| `MNDWI` | Float | dimensionless | −1 to 1 | Landsat-8/9 | (B3−B6)/(B3+B6) | Xu (2006) |
| `Albedo` | Float | dimensionless | 0 to 1 | Landsat-8/9 | Liang (2001) broadband | Liang (2001) |

### Interpretation Guide

| Index | Positive Values Mean | Negative Values Mean | UHI Relevance |
|-------|---------------------|---------------------|---------------|
| NDVI | Dense vegetation (cooling) | Bare soil/water | Inverse correlation with LST |
| NDBI | Built-up surfaces (heating) | Vegetation/water | Positive correlation with LST |
| NDWI | Open water (cooling) | Dry land | Water bodies reduce nearby LST |
| MNDWI | Water (better urban accuracy) | Non-water | Improved NDWI for cities |
| Albedo | Reflective surface | Absorptive surface | Low albedo → more heat absorption |

---

## Land Cover Features

| Feature | Type | Units | Valid Range | Source | Resolution |
|---------|------|-------|-------------|--------|------------|
| `LULC_ESA` | Integer | class code | 10–100 | ESA WorldCover v200 | 10m |
| `LULC_DW` | Integer | class code | 0–8 | Dynamic World | 10m |
| `Impervious_Frac` | Binary | 0/1 | 0 or 1 | GAIA | 30m |
| `Tree_Cover_Pct` | Integer | % | 0–100 | Hansen GFC | 30m |

### ESA WorldCover Classes
| Code | Class | Heat Impact |
|------|-------|-------------|
| 10 | Tree Cover | Strong cooling |
| 20 | Shrubland | Moderate cooling |
| 30 | Grassland | Mild cooling |
| 40 | Cropland | Seasonal (dry = heating) |
| 50 | Built-up | Strong heating |
| 60 | Bare/Sparse | Moderate heating |
| 80 | Water | Strong cooling |

### Dynamic World Classes
| Code | Class |
|------|-------|
| 0 | Water |
| 1 | Trees |
| 2 | Grass |
| 3 | Flooded Vegetation |
| 4 | Crops |
| 5 | Shrub/Scrub |
| 6 | Built Area |
| 7 | Bare Ground |
| 8 | Snow/Ice |

---

## Weather Variables

| Feature | Type | Units | Typical Range | Source | GEE Band |
|---------|------|-------|---------------|--------|----------|
| `AirTemp` | Float | °C | 15–50 (India summer) | ERA5-Land | temperature_2m |
| `Humidity` | Float | % | 10–100 | ERA5-Land (derived) | Magnus formula |
| `WindSpeed` | Float | m/s | 0–15 | ERA5-Land | sqrt(U²+V²) |
| `WindDirection` | Float | degrees | 0–360 | ERA5-Land | atan2(−U,−V) |
| `SolarRadiation` | Float | W/m² | 50–400 | ERA5-Land | SSRD ÷ 3600 |
| `Pressure` | Float | hPa | 900–1050 | ERA5-Land | surface_pressure ÷ 100 |
| `Rainfall` | Float | mm | 0–500+ | ERA5-Land | total_precip × 1000 |

### Humidity Calculation (Magnus Formula)
```
RH = 100 × exp[(17.625 × Td) / (243.04 + Td)] / exp[(17.625 × T) / (243.04 + T)]
```
Where T = air temperature (°C), Td = dewpoint temperature (°C).  
Reference: Alduchov & Eskridge (1996).

---

## Terrain Features

| Feature | Type | Units | Valid Range | Source | Method |
|---------|------|-------|-------------|--------|--------|
| `Elevation` | Float | meters | 0–8848 | SRTM v3 | Direct |
| `Slope` | Float | degrees | 0–90 | SRTM v3 | ee.Terrain.products() |
| `Aspect` | Float | degrees | 0–360 | SRTM v3 | ee.Terrain.products() |

---

## Urban Morphology Features

| Feature | Type | Units | Valid Range | Source | Method |
|---------|------|-------|-------------|--------|--------|
| `Building_Density` | Float | fraction or m² | varies | GHSL GHS-BUILT-S | Direct |
| `Building_Height` | Float | meters | 0–200+ | GHSL GHS-BUILT-H | Direct |
| `Building_Volume` | Float | m³/pixel | ≥ 0 | Derived | Density × Height |
| `Nighttime_Lights` | Float | nW/cm²/sr | 0–300+ | VIIRS DNB | Median composite |
| `Population_Density` | Float | people/pixel | 0–10000+ | WorldPop 100m | Direct |

---

## Distance Features

| Feature | Type | Units | Valid Range | Source | Method |
|---------|------|-------|-------------|--------|--------|
| `Dist_Water` | Float | meters | 0–50000+ | Derived from NDWI | Euclidean distance to NDWI > 0 |
| `Dist_Green` | Float | meters | 0–30000+ | Derived from NDVI | Euclidean distance to NDVI > 0.4 |

---

## Derived Features

| Feature | Type | Units | Valid Range | Source | Method |
|---------|------|-------|-------------|--------|--------|
| `Green_Space_Density` | Float | fraction | 0–1 | Derived from NDVI | Mean of (NDVI > 0.3) in 150m radius |
| `Surface_Roughness` | Float | meters | ≥ 0 | Derived from SRTM | StdDev of elevation in 150m radius |
| `Anthropogenic_Heat` | Float | unitless | 0–1 | Derived | NTL_norm × Pop_norm |
| `Road_Density_Proxy` | Float | unitless | 0–1 | Derived | Impervious − (LULC == Built-up) |

---

## Heat Indices

| Feature | Type | Units | Valid Range | Source | Formula | Reference |
|---------|------|-------|-------------|--------|---------|-----------|
| `UHI_Intensity` | Float | °C | −10 to +15 | Derived | LST − mean(rural LST) | Oke (1982) |
| `UTFVI` | Float | dimensionless | −0.1 to 0.1 | Derived | (LST − mean LST) / mean LST | Guha et al. (2018) |

### UTFVI Classification
| UTFVI Range | UHI Strength | Ecological Quality |
|-------------|-------------|-------------------|
| < 0 | None | Excellent |
| 0 – 0.005 | Weak | Good |
| 0.005 – 0.010 | Moderate | Normal |
| 0.010 – 0.015 | Strong | Bad |
| 0.015 – 0.020 | Stronger | Worse |
| > 0.020 | Strongest | Worst |

---

## Quality Metadata

| Feature | Type | Units | Valid Range | Source | Description |
|---------|------|-------|-------------|--------|-------------|
| `QualityScore` | Integer | count | 0–30+ | Derived | Number of valid Landsat observations used in median composite |

Higher QualityScore = more observations = more reliable composite.

---

## Features NOT Computable from GEE

| Feature | Reason | Potential Alternative |
|---------|--------|---------------------|
| Sky View Factor | Requires 3D LiDAR or DSM > 1m | GHSL building height as proxy |
| Street Width | Requires cadastral/OSM vector data | Road Density Proxy |
| Street Canyon Geometry | Requires 3D urban model | Building Height + Density |
| Traffic Density | Requires transport authority data | Nighttime Lights as proxy |
| Industrial Zone Density | Requires zoning maps | LULC + Nighttime Lights |
| UTCI (Universal Thermal Climate Index) | Requires iterative bioclimate solver | UHI Intensity + Humidity as proxy |
