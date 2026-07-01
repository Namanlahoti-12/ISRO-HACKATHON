# Data Sources

Complete reference for all datasets used in the Urban Heat AI pipeline.

---

## Satellite Imagery

### Landsat-8 Collection 2 Level 2
| Property | Value |
|----------|-------|
| **GEE Collection** | `LANDSAT/LC08/C02/T1_L2` |
| **Provider** | USGS |
| **Spatial Resolution** | 30m (optical), 100m (thermal, resampled to 30m) |
| **Temporal Resolution** | 16-day revisit |
| **Available Since** | April 2013 |
| **Bands Used** | SR_B2–SR_B7 (reflectance), ST_B10 (surface temp), QA_PIXEL |
| **Processing Level** | Level 2 — atmospherically corrected surface reflectance and temperature |
| **Scale Factors** | Reflectance: ×0.0000275 + (−0.2); Temperature: ×0.00341802 + 149.0 |
| **Citation** | USGS Landsat Collection 2 Science Product Guide |

### Landsat-9 Collection 2 Level 2
| Property | Value |
|----------|-------|
| **GEE Collection** | `LANDSAT/LC09/C02/T1_L2` |
| **Provider** | USGS |
| **Spatial Resolution** | 30m (optical), 100m (thermal) |
| **Available Since** | October 2021 |
| **Notes** | Identical band structure to Landsat-8. Merged with L8 for denser composites. |

### Sentinel-2 Surface Reflectance (Harmonized)
| Property | Value |
|----------|-------|
| **GEE Collection** | `COPERNICUS/S2_SR_HARMONIZED` |
| **Provider** | ESA / Copernicus |
| **Spatial Resolution** | 10m (B2–B4, B8), 20m (B5–B7, B8A, B11–B12) |
| **Temporal Resolution** | 5-day revisit (combined S2A + S2B) |
| **Bands Used** | B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12, QA60 |
| **Scale Factor** | Divide by 10000 |
| **Citation** | Copernicus Sentinel-2 Mission |

---

## Weather & Climate

### ERA5-Land Hourly
| Property | Value |
|----------|-------|
| **GEE Collection** | `ECMWF/ERA5_LAND/HOURLY` |
| **Provider** | ECMWF (Copernicus Climate Change Service) |
| **Spatial Resolution** | ~11 km (0.1°) |
| **Temporal Resolution** | Hourly |
| **Variables Used** | temperature_2m, dewpoint_temperature_2m, u/v_component_of_wind_10m, surface_solar_radiation_downwards_hourly, surface_pressure, total_precipitation_hourly |
| **Citation** | Muñoz Sabater, J. (2019). ERA5-Land hourly data. ECMWF. |

---

## Land Cover

### ESA WorldCover v200
| Property | Value |
|----------|-------|
| **GEE Collection** | `ESA/WorldCover/v200` |
| **Spatial Resolution** | 10m |
| **Reference Year** | 2021 |
| **Classes** | 11 (Trees, Shrub, Grass, Crop, Built-up, Bare, Snow, Water, Wetland, Mangroves, Moss) |
| **Overall Accuracy** | 76.7% |
| **Citation** | Zanaga, D. et al. (2022). ESA WorldCover 10m 2021. |

### Google Dynamic World
| Property | Value |
|----------|-------|
| **GEE Collection** | `GOOGLE/DYNAMICWORLD/V1` |
| **Spatial Resolution** | 10m |
| **Temporal Resolution** | Near real-time (per Sentinel-2 image) |
| **Classes** | 9 (Water, Trees, Grass, Flooded Veg, Crops, Shrub, Built, Bare, Snow) |
| **Citation** | Brown, C.F. et al. (2022). Dynamic World. Nature Scientific Data. |

### GAIA Impervious Surface
| Property | Value |
|----------|-------|
| **GEE Collection** | `Tsinghua/FROM-GLC/GAIA/v10` |
| **Spatial Resolution** | 30m |
| **Temporal Coverage** | 1985–2018 |
| **Citation** | Gong, P. et al. (2020). Annual maps of global artificial impervious area. |

### Hansen Global Forest Change
| Property | Value |
|----------|-------|
| **GEE Collection** | `UMD/hansen/global_forest_change_2023_v1_11` |
| **Spatial Resolution** | 30m |
| **Band Used** | treecover2000 (% canopy cover in year 2000) |
| **Citation** | Hansen, M.C. et al. (2013). High-resolution global maps of forest cover change. Science. |

---

## Urban Infrastructure

### GHSL Built-up Surface (GHS-BUILT-S)
| Property | Value |
|----------|-------|
| **GEE Collection** | `JRC/GHSL/P2023A/GHS_BUILT_S` |
| **Provider** | JRC (European Commission) |
| **Spatial Resolution** | 10m |
| **Content** | Built-up surface fraction per pixel |
| **Citation** | Pesaresi, M. et al. (2023). GHS-BUILT-S R2023A. JRC. |

### GHSL Building Height (GHS-BUILT-H)
| Property | Value |
|----------|-------|
| **GEE Collection** | `JRC/GHSL/P2023A/GHS_BUILT_H` |
| **Spatial Resolution** | 100m |
| **Content** | Average building height (meters) per pixel |
| **Citation** | Pesaresi, M. et al. (2023). GHS-BUILT-H R2023A. JRC. |

### VIIRS Day/Night Band (Nighttime Lights)
| Property | Value |
|----------|-------|
| **GEE Collection** | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` |
| **Provider** | NOAA |
| **Spatial Resolution** | ~500m |
| **Band Used** | avg_rad (average radiance in nW/cm²/sr) |
| **Citation** | Elvidge, C.D. et al. (2017). VIIRS Nighttime Lights. Remote Sensing. |

---

## Population

### WorldPop
| Property | Value |
|----------|-------|
| **GEE Collection** | `WorldPop/GP/100m/pop` |
| **Spatial Resolution** | 100m |
| **Content** | UN-adjusted population count per grid cell |
| **Citation** | Tatem, A.J. (2017). WorldPop. Scientific Data. |

---

## Terrain

### SRTM v3
| Property | Value |
|----------|-------|
| **GEE Collection** | `USGS/SRTMGL1_003` |
| **Spatial Resolution** | 30m |
| **Content** | Digital elevation model (meters above sea level) |
| **Derived Products** | Slope (°), Aspect (°) via ee.Terrain.products() |
| **Citation** | Farr, T.G. et al. (2007). The Shuttle Radar Topography Mission. Reviews of Geophysics. |

---

## Administrative Boundaries

### FAO GAUL Level 2
| Property | Value |
|----------|-------|
| **GEE Collection** | `FAO/GAUL/2015/level2` |
| **Content** | District-level administrative boundaries |
| **Used For** | Study area definition when USE_ADMIN_BOUNDARY = true |

---

## Datasets NOT Available in GEE

| Dataset | Why Not Available | Alternative Used |
|---------|-------------------|------------------|
| OpenStreetMap Buildings | Requires external API | GHSL Built-up Surface |
| Microsoft Building Footprints | Not in GEE catalog | GHSL Built-up Surface |
| OpenStreetMap Roads | Vector data, requires OSM API | Road Density Proxy (Impervious − Built-up) |
| HydroSHEDS | Available but coarse resolution | NDWI-based water detection |
| Copernicus DEM | Available; SRTM preferred for consistency | SRTM 30m |
| NASA ECOSTRESS | Limited temporal coverage | Landsat-8/9 LST |
| MODIS LST | Used for validation, not primary data | Landsat-8/9 LST (higher resolution) |
