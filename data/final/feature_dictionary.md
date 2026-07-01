# Feature Dictionary - Master Dataset

Generated: 2026-06-29 18:01:11

Total columns: 92

---

## Metadata Columns

| Column | Type | Description |
|--------|------|-------------|
| PixelID | int | Sequential pixel identifier |
| Latitude | float | WGS84 latitude (degrees) |
| Longitude | float | WGS84 longitude (degrees) |
| Timestamp | string | Composite date range |

## Target Variable

| Column | Units | Range | Description |
|--------|-------|-------|-------------|
| LST | Celsius | 21.78 - 53.52 | Land Surface Temperature |

## Spectral Indices

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| NDVI | dimensionless | -0.1 | 0.799 | 0.388649 | Vegetation health (NIR-Red)/(NIR+Red) |
| NDBI | dimensionless | -0.2999 | 0.3483 | -0.079718 | Built-up surfaces (SWIR-NIR)/(SWIR+NIR) |
| NDWI | dimensionless | -0.4997 | 0.5987 | -0.165247 | Water bodies (Green-NIR)/(Green+NIR) |
| MNDWI | dimensionless | -0.5949 | 0.6768 | -0.163325 | Modified water index (Green-SWIR)/(Green+SWIR) |
| SAVI | dimensionless | -0.1 | 0.799 | 0.388649 | Soil-adjusted vegetation (Huete 1988, L=0.5) |
| Albedo | fraction | 0.0803 | 0.3499 | 0.214786 | Surface reflectivity (Liang 2001) |

## Land Cover

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| LULC_ESA | class code | 10.0 | 80.0 | 41.262707 | ESA WorldCover class (10m) |
| LULC_DW | class code | 0.0 | 7.0 | 3.548957 | Dynamic World class (10m) |
| Impervious_Frac | binary | 0.0 | 1.0 | 0.132691 | Impervious surface flag (GAIA) |
| Tree_Cover_Pct | % | 0.0 | 80.0 | 29.820171 | Tree canopy cover % (Hansen) |

## Weather

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| AirTemp | Celsius | 27.76 | 42.48 | 34.982413 | 2m air temperature (ERA5-Land) |
| Humidity | % | 25.0 | 64.98 | 44.92107 | Relative humidity (Magnus formula) |
| WindSpeed | m/s | 1.0 | 5.0 | 2.960717 | 10m wind speed (ERA5-Land) |
| WindDirection | degrees | 0.0 | 359.7 | 180.774692 | Wind direction meteorological (ERA5) |
| SolarRadiation | W/m2 | 180.02 | 319.97 | 249.045795 | Downward shortwave radiation (ERA5) |
| Cloud_Cover_Proxy | fraction | 0.0858 | 0.4857 | 0.288441 | Cloud cover estimate (1-SR/350) |
| Pressure | hPa | 990.01 | 1014.99 | 1002.54099 | Surface pressure (ERA5-Land) |
| Rainfall | mm | 0.01 | 149.97 | 73.774735 | Accumulated precipitation (ERA5) |

## Terrain

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| Elevation | meters | 200.1 | 280.0 | 239.210059 | Terrain height ASL (SRTM 30m) |
| Slope | degrees | 0.0 | 5.0 | 2.532846 | Terrain slope angle (SRTM) |
| Aspect | degrees | 0.3 | 359.8 | 184.321723 | Terrain aspect direction (SRTM) |

## Urban Morphology

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| Building_Density | fraction | 0.0 | 89.96 | 12.196624 | Built-up surface fraction (GHSL) |
| Building_Height | meters | 0.0 | 29.89 | 4.546891 | Average building height (GHSL) |
| Building_Volume | m3/pixel | 0.0 | 2633.19 | 157.851386 | Building volume proxy (density x height) |
| Road_Density_Proxy | unitless | -0.1 | 0.4994 | 0.034784 | Road density (impervious - built-up) |
| Street_Width_Proxy | meters | 5.0 | 17.485 | 6.39324 | Estimated street width (5-30m) |
| Nighttime_Lights | nW/cm2/sr | 0.0 | 59.79 | 9.597592 | VIIRS nighttime radiance |
| Population_Density | people/pixel | 0.0 | 1999.9 | 187.777582 | Gridded population (WorldPop 100m) |

## Distance Features

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| Dist_Water | meters | 6.8 | 4995.2 | 2533.367309 | Distance to nearest water body |
| Dist_Green | meters | 0.2 | 2992.9 | 962.667683 | Distance to nearest green space |

## Heat Indices

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| UHI_Intensity | Celsius | -14.22 | 17.52 | 0.007346 | LST minus rural mean LST |
| UTFVI | dimensionless | -0.4269 | 0.4083 | -0.052438 | Urban Thermal Field Variance Index |
| UTCI_Approx | Celsius | 25.22 | 40.73 | 31.838999 | Approximate Universal Thermal Climate Index |

## Derived / Proxy

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| Anthropogenic_Heat | unitless | 0.0 | 0.7997 | 0.101912 | Waste heat proxy (NTL x Pop) |
| Green_Space_Density | fraction | 0.0001 | 0.769 | 0.27473 | Green fraction in 150m neighborhood |
| Surface_Roughness | meters | 0.5 | 7.99 | 4.324735 | Elevation StdDev in 150m neighborhood |

## Quality

| Column | Units | Min | Max | Mean | Description |
|--------|-------|-----|-----|------|-------------|
| QualityScore | count | 2.0 | 18.0 | 10.003745 | Valid Landsat observations count |

## One-Hot Encoded LULC

| Column | Type | Description |
|--------|------|-------------|
| LULC_DW_Bare | binary (0/1) | Land cover class indicator |
| LULC_DW_Built | binary (0/1) | Land cover class indicator |
| LULC_DW_Crops | binary (0/1) | Land cover class indicator |
| LULC_DW_Flooded_Veg | binary (0/1) | Land cover class indicator |
| LULC_DW_Grass | binary (0/1) | Land cover class indicator |
| LULC_DW_Shrub | binary (0/1) | Land cover class indicator |
| LULC_DW_Trees | binary (0/1) | Land cover class indicator |
| LULC_DW_Water | binary (0/1) | Land cover class indicator |
| LULC_ESA_Bare | binary (0/1) | Land cover class indicator |
| LULC_ESA_Built_up | binary (0/1) | Land cover class indicator |
| LULC_ESA_Cropland | binary (0/1) | Land cover class indicator |
| LULC_ESA_Grassland | binary (0/1) | Land cover class indicator |
| LULC_ESA_Shrubland | binary (0/1) | Land cover class indicator |
| LULC_ESA_Trees | binary (0/1) | Land cover class indicator |
| LULC_ESA_Water | binary (0/1) | Land cover class indicator |

## Normalized Features

| Column | Method | Description |
|--------|--------|-------------|
| AirTemp_zscore | StandardScaler (mean=0, std=1) | Normalized AirTemp |
| Albedo_norm | MinMaxScaler [0, 1] | Normalized Albedo |
| Anthropogenic_Heat_zscore | StandardScaler (mean=0, std=1) | Normalized Anthropogenic_Heat |
| Aspect_cos | Circular cos encoding | Normalized Aspect |
| Aspect_sin | Circular sin encoding | Normalized Aspect |
| Building_Density_zscore | StandardScaler (mean=0, std=1) | Normalized Building_Density |
| Building_Height_zscore | StandardScaler (mean=0, std=1) | Normalized Building_Height |
| Building_Volume_zscore | StandardScaler (mean=0, std=1) | Normalized Building_Volume |
| Dist_Green_zscore | StandardScaler (mean=0, std=1) | Normalized Dist_Green |
| Dist_Water_zscore | StandardScaler (mean=0, std=1) | Normalized Dist_Water |
| Elevation_zscore | StandardScaler (mean=0, std=1) | Normalized Elevation |
| Green_Space_Density_norm | MinMaxScaler [0, 1] | Normalized Green_Space_Density |
| Humidity_zscore | StandardScaler (mean=0, std=1) | Normalized Humidity |
| Impervious_Frac_norm | MinMaxScaler [0, 1] | Normalized Impervious_Frac |
| LST_zscore | StandardScaler (mean=0, std=1) | Normalized LST |
| MNDWI_norm | MinMaxScaler [0, 1] | Normalized MNDWI |
| NDBI_norm | MinMaxScaler [0, 1] | Normalized NDBI |
| NDVI_norm | MinMaxScaler [0, 1] | Normalized NDVI |
| NDWI_norm | MinMaxScaler [0, 1] | Normalized NDWI |
| Nighttime_Lights_zscore | StandardScaler (mean=0, std=1) | Normalized Nighttime_Lights |
| Population_Density_zscore | StandardScaler (mean=0, std=1) | Normalized Population_Density |
| Pressure_zscore | StandardScaler (mean=0, std=1) | Normalized Pressure |
| QualityScore_norm | MinMaxScaler [0, 1] | Normalized QualityScore |
| Rainfall_zscore | StandardScaler (mean=0, std=1) | Normalized Rainfall |
| Road_Density_Proxy_norm | MinMaxScaler [0, 1] | Normalized Road_Density_Proxy |
| SAVI_norm | MinMaxScaler [0, 1] | Normalized SAVI |
| Slope_zscore | StandardScaler (mean=0, std=1) | Normalized Slope |
| SolarRadiation_zscore | StandardScaler (mean=0, std=1) | Normalized SolarRadiation |
| Surface_Roughness_zscore | StandardScaler (mean=0, std=1) | Normalized Surface_Roughness |
| Tree_Cover_Pct_norm | MinMaxScaler [0, 1] | Normalized Tree_Cover_Pct |
| UHI_Intensity_zscore | StandardScaler (mean=0, std=1) | Normalized UHI_Intensity |
| UTFVI_zscore | StandardScaler (mean=0, std=1) | Normalized UTFVI |
| WindDirection_cos | Circular cos encoding | Normalized WindDirection |
| WindDirection_sin | Circular sin encoding | Normalized WindDirection |
| WindSpeed_zscore | StandardScaler (mean=0, std=1) | Normalized WindSpeed |

## Preprocessing Steps

| Step | Name | Detail |
|------|------|--------|
| 01 | Load CSV | UrbanHeatAI\data\raw\Delhi_UHI_MasterDataset.csv | 2,000 rows x 39 cols |
| 02 | Schema validation | All 39 expected columns present |
| 03 | CRS validation | All coordinates valid WGS84 (EPSG:4326) |
| 04 | Timestamps | 1 unique timestamp(s). All pixels share the same composite period (temporal alignment inherent). |
| 05 | Range clamping | 55 individual values clamped to valid ranges |
| 05 | Invalid removal total | 0 total rows removed |
| 06 | Cloud filter | Removed 131 pixels with QualityScore < 2 (< 2 valid observations = mostly cloudy) |
| 07 | Duplicates | No duplicates found |
| 08 | Compute Street Width | Proxy = Road_Density * 25 + 5 (estimated 5-30m range) |
| 08 | Compute UTCI | Approximate UTCI from Blazejczyk et al. (2012) simplified model |
| 08 | Compute Cloud Cover | Proxy = 1 - SR/350 (inverse solar radiation fraction) |
| 08 | Derived features | 3 new features computed |
| 09 | Missing summary | 2 columns have missing values (51 total NaN cells) |
| 09 |   Impute Building_Height | 37 NaN -> 0 (absence = no urban feature) |
| 09 |   Impute Nighttime_Lights | 14 NaN -> 0 (absence = no urban feature) |
| 09 | Missing values resolved | 51 NaN -> 0 remaining |
| 10 | Encode LULC_ESA | 7 classes -> 7 binary columns |
| 10 | Encode LULC_DW | 8 classes -> 8 binary columns |
| 10 | Encoding complete | 15 one-hot columns created from 2 categoricals |
| 11 | StandardScaler | 20 features -> z-score normalized (mean=0, std=1) |
| 11 | MinMaxScaler | 11 features -> [0,1] normalized |
| 11 | Circular encoding | Aspect + WindDirection -> sin/cos components |
| 12 | Final dataset | 1869 rows x 92 columns |
| 13 | master_dataset.csv | Saved (1374.5 KB) |
| 13 | Data splits | Train: 1308 | Val: 280 | Test: 281 |
| 13 | metadata.json | Saved (28.5 KB) |

