# Project Overview

## ISRO Bharatiya Antariksh Hackathon — Urban Heat Stress Mapping

### Problem Statement

Urban Heat Islands (UHIs) are metropolitan areas significantly warmer than surrounding rural areas. In Indian cities, this effect is intensifying due to rapid urbanization, loss of green cover, and increased impervious surfaces. UHI increases energy consumption, worsens air quality, and creates health risks for millions.

### Our Objective

Build an **AI-powered system** that:
1. **Identifies** UHI hotspots at fine spatial resolution (30m)
2. **Explains** the causes of localized heat (why is this spot hot?)
3. **Recommends** cooling interventions (what can be done to reduce heat?)

### Scientific Approach

We use a multi-source remote sensing approach combining:
- **Thermal remote sensing** (Landsat-8/9) for surface temperature
- **Optical remote sensing** (Sentinel-2) for high-resolution land cover
- **Weather reanalysis** (ERA5-Land) for atmospheric conditions
- **Urban datasets** (GHSL, VIIRS, WorldPop) for human activity
- **Terrain data** (SRTM) for topographic effects

This multi-factor approach follows the methodology established in peer-reviewed UHI research (Voogt & Oke, 2003; Zhou et al., 2017; Guha et al., 2018).

### Current Phase: Data Collection & Feature Engineering

This phase focuses on:
- Collecting 15+ datasets via Google Earth Engine
- Computing 37+ features per pixel location
- Exporting an AI-ready master dataset (CSV)
- Creating georeferenced maps (GeoTIFF)

### Why This Approach?

| Decision | Rationale |
|----------|-----------|
| Google Earth Engine | Free cloud computing, no download/storage of TB-scale satellite data |
| Landsat + Sentinel-2 | Complementary: Landsat has thermal, Sentinel-2 has higher spatial resolution |
| ERA5-Land over station data | Gridded, gap-free, consistent coverage across all Indian cities |
| Multiple LULC sources | Cross-validation: ESA WorldCover (accuracy), Dynamic World (recency) |
| 30m export resolution | Matches Landsat native resolution; balance of detail vs. file size |
| CSV as primary output | Universal format compatible with all ML frameworks |

### Key Scientific References

1. Voogt, J.A. & Oke, T.R. (2003). Thermal remote sensing of urban climates. *Remote Sensing of Environment*, 86(3), 370-384.
2. Zhou, D. et al. (2017). Surface urban heat island in China's 32 major cities. *Remote Sensing of Environment*, 195, 44-57.
3. Guha, S. et al. (2018). Analytical study of land surface temperature with NDVI and NDBI using Landsat 8 OLI and TIRS data. *Annals of GIS*, 24(4), 241-255.
4. Sobrino, J.A. et al. (2004). Land surface temperature retrieval from LANDSAT TM 5. *Remote Sensing of Environment*, 90(4), 434-440.
5. Liang, S. (2001). Narrowband to broadband conversions of land surface albedo. *Remote Sensing of Environment*, 76(2), 213-238.
