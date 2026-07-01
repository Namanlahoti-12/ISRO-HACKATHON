# Urban Heat AI

## AI-Powered Urban Heat Stress Mapping & Cooling Optimization System

**ISRO Bharatiya Antariksh Hackathon**

An end-to-end geospatial AI pipeline that identifies Urban Heat Island (UHI) hotspots in Indian cities using satellite imagery, weather reanalysis, and urban morphology data from 15+ authoritative sources — combined with a **Physics-Informed Cooling Optimization Engine** that recommends evidence-based cooling interventions.

---

## 🏗 Architecture

```
UrbanHeatAI/
├── gee/                         # Google Earth Engine scripts
│   ├── main.js                  # ★ Complete runnable pipeline (copy into GEE)
│   ├── config.js                # Configuration module (reference)
│   ├── cloudMask.js             # Cloud/shadow masking functions
│   ├── lst.js                   # Land Surface Temperature + heat indices
│   ├── ndvi.js                  # Vegetation index
│   ├── ndbi.js                  # Built-up index
│   ├── ndwi.js                  # Water index
│   ├── mndwi.js                 # Modified water index
│   ├── lulc.js                  # Land cover (3 sources)
│   ├── weather.js               # ERA5 weather (8 variables)
│   ├── morphology.js            # Terrain, buildings, lights, distances
│   ├── population.js            # Population density
│   ├── exports.js               # Export utilities
│   └── legacy_v1.js             # Original v1 script (archived)
├── models/                      # ML training pipeline
│   ├── train_model.py           # ★ Hybrid regression + classification trainer
│   └── output/                  # Trained artifacts
│       ├── trained_model.pkl    # Best model bundle (GradientBoosting)
│       ├── model_metrics.json   # Performance metrics for all 6 models
│       ├── feature_importance.csv
│       ├── confusion_matrix.png
│       ├── shap_summary.png
│       └── training_report.md
├── cooling_engine/              # ★ Physics-Informed Cooling Optimization
│   ├── __init__.py              # Package init
│   ├── intervention_library.py  # 31 interventions (Green/White/Blue/Grey)
│   ├── hotspot_detector.py      # Hotspot detection & zone clustering
│   ├── feature_modifier.py      # Physics-based feature modification
│   ├── optimizer.py             # NSGA-II multi-objective optimization
│   ├── cooling_engine.py        # Main orchestrator
│   ├── report_generator.py      # CSV/JSON output reports
│   └── map_generator.py         # Before/After/Priority heat maps
├── backend/                     # Flask API server
│   └── app.py                   # REST API for Scenario Simulator
├── frontend/                    # Interactive Dashboard
│   ├── index.html               # Scenario Simulator UI
│   ├── index.css                # Premium glassmorphism styles
│   └── app.js                   # Chart.js visualizations & API calls
├── docs/                        # Technical documentation
├── data/                        # Data storage (raw → processed → final)
│   ├── raw/                     # Downloaded from Google Drive
│   ├── intermediate/            # Partially processed
│   ├── processed/               # Feature layers
│   ├── final/                   # AI-ready datasets (master_dataset.csv)
│   └── metadata/                # Data dictionaries
├── utils/                       # Python helper scripts
│   ├── gee_validator.py         # Static analysis for GEE scripts
│   ├── prepare_ml_dataset.py    # Dataset merging utility
│   └── explain_prediction.py    # Per-pixel SHAP explanations
├── outputs/                     # Generated analysis outputs
│   └── cooling_analysis/        # Cooling engine outputs
│       ├── recommendations.json # Intervention recommendations
│       ├── optimization_results.csv
│       ├── before_after_predictions.csv
│       ├── intervention_library.json
│       ├── heatmap_before.png
│       ├── heatmap_after.png
│       ├── heatmap_difference.png
│       ├── heatmap_cooling_potential.png
│       └── heatmap_priority.png
└── requirements.txt             # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites
- [Google Earth Engine account](https://earthengine.google.com/signup/) (free for research)
- Google Drive with ~5 GB free space
- Python 3.9+ with pip

### Installation

```bash
cd UrbanHeatAI
pip install -r requirements.txt
```

### Step 1: Collect Data (Google Earth Engine)

1. **Open** [Google Earth Engine Code Editor](https://code.earthengine.google.com)
2. **Create** a new script: File → New
3. **Copy** the entire contents of `gee/main.js` into the editor
4. **Edit** Section 1 (Configuration) for your target city:
   ```javascript
   var CITY_NAME  = 'Mumbai';     // Your city
   var CENTER_LAT = 19.0760;      // Latitude
   var CENTER_LON = 72.8777;      // Longitude
   ```
5. **Click** "Run"
6. **Go to** Tasks tab (top-right) → Click "Run" on each export task
7. **Download** files from Google Drive → `data/raw/`

### Step 2: Train ML Models

```bash
python models/train_model.py --input data/final/master_dataset.csv --output-dir models/output
```

This trains 6 models (RandomForest, XGBoost, LightGBM, CatBoost, ExtraTrees, GradientBoosting) for both regression and classification, and selects the best one automatically.

### Step 3: Run Cooling Optimization Engine

```bash
python -m cooling_engine.cooling_engine --data data/final/master_dataset.csv --city Delhi
```

This runs the full pipeline:
1. Loads the trained model
2. Detects UHI hotspots (High + Extreme classes)
3. Clusters hotspots into intervention zones
4. Runs NSGA-II multi-objective optimization
5. Applies the best intervention package
6. Generates reports (JSON/CSV) and heat maps (PNG)

### Step 4: Launch Interactive Dashboard

```bash
python backend/app.py
```

Open **http://localhost:5000** in your browser to access the **Cooling Scenario Simulator**.

### Indian City Quick Reference
| City | Latitude | Longitude |
|------|----------|-----------|
| Delhi | 28.6139 | 77.2090 |
| Mumbai | 19.0760 | 72.8777 |
| Bangalore | 12.9716 | 77.5946 |
| Chennai | 13.0827 | 80.2707 |
| Hyderabad | 17.3850 | 78.4867 |
| Kolkata | 22.5726 | 88.3639 |
| Pune | 18.5204 | 73.8567 |
| Ahmedabad | 23.0225 | 72.5714 |
| Jaipur | 26.9124 | 75.7873 |

---

## 📊 Features (37 Variables)

| Category | Features | Count |
|----------|----------|-------|
| **Spectral** | LST, NDVI, NDBI, NDWI, MNDWI, Albedo | 6 |
| **Land Cover** | LULC_ESA, LULC_DW, Impervious, TreeCover | 4 |
| **Weather** | AirTemp, Humidity, WindSpeed, WindDir, Solar, Pressure, Rain | 7 |
| **Terrain** | Elevation, Slope, Aspect | 3 |
| **Urban** | BuildDensity, BuildHeight, BuildVol, NightLights, Population | 5 |
| **Distance** | Dist_Water, Dist_Green | 2 |
| **Derived** | GreenDensity, Roughness, AnthroHeat, RoadProxy | 4 |
| **Heat Index** | UHI_Intensity, UTFVI | 2 |
| **Quality** | QualityScore | 1 |
| **Metadata** | PixelID, Latitude, Longitude, Timestamp | 4 |

---

## 📦 Data Sources (15 Datasets)

| Dataset | Resolution | Provider |
|---------|-----------|----------|
| Landsat-8 C2 L2 | 30m | USGS |
| Landsat-9 C2 L2 | 30m | USGS |
| Sentinel-2 SR | 10m | ESA/Copernicus |
| ERA5-Land | ~11 km | ECMWF |
| ESA WorldCover | 10m | ESA |
| Dynamic World | 10m | Google/WRI |
| GAIA Impervious | 30m | Tsinghua |
| Hansen Forest | 30m | UMD |
| SRTM DEM | 30m | NASA |
| GHSL Built-up | 10m | JRC |
| GHSL Height | 100m | JRC |
| VIIRS Nighttime | 500m | NOAA |
| WorldPop | 100m | WorldPop |
| FAO GAUL | Admin | FAO |

---

## 🧊 Cooling Optimization Engine

The **Physics-Informed Urban Cooling Optimization Engine** integrates with the trained AI model to recommend evidence-based cooling interventions for detected UHI hotspots.

### How It Works

```
Trained Model → Detect Hotspots → Profile Features → NSGA-II Optimization
                                                          ↓
                                      Best Intervention Package
                                                          ↓
                                    Modified Features → Re-predict Heat Score
                                                          ↓
                                    Before/After Maps + Recommendations Report
```

### Intervention Library (31 Interventions)

| Category | Count | Avg Cooling | Examples |
|----------|-------|-------------|----------|
| 🌿 **Green** | 8 | 1.39°C | Street Trees, Urban Forests, Green Roofs, Bioswales |
| ⬜ **White** | 5 | 1.04°C | Cool Roofs, Cool Pavements, Reflective Concrete |
| 💧 **Blue** | 9 | 1.64°C | Lake Restoration, Ponds, Rain Gardens, Misting |
| 🏗️ **Grey** | 9 | 1.44°C | Wind Corridors, Jaali Structures, Shading |

Each intervention includes:
- Physics-based feature effect parameters (delta NDVI, Albedo, etc.)
- Cost per unit with annual maintenance
- Feasibility score and Indian suitability rating
- Co-benefits list and implementation constraints

### Optimization

Uses **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) to find Pareto-optimal intervention combinations balancing:
- **Objective 1**: Maximize temperature reduction
- **Objective 2**: Minimize total cost
- **Objective 3**: Maximize feasibility
- **Objective 4**: Maximize co-benefits

### Generated Outputs

| Output | Description |
|--------|-------------|
| `recommendations.json` | Full intervention recommendations with zone-level analysis |
| `optimization_results.csv` | All Pareto-optimal solutions with costs & coverages |
| `before_after_predictions.csv` | Per-pixel before/after heat scores |
| `intervention_library.json` | Complete intervention catalog |
| `heatmap_before.png` | Original heat score distribution |
| `heatmap_after.png` | Predicted post-intervention heat scores |
| `heatmap_difference.png` | Temperature reduction per pixel |
| `heatmap_cooling_potential.png` | Maximum achievable cooling per area |
| `heatmap_priority.png` | Intervention priority ranking |

### Scenario Simulator Dashboard

The interactive web dashboard (`http://localhost:5000`) lets you:
- Adjust 7 intervention sliders (tree cover, cool roofs, green roofs, water bodies, albedo, impervious reduction, building density)
- See **real-time heat score predictions** using the trained model
- View before/after class distribution charts
- Examine per-feature impact tables

---

## 🎯 ML Pipeline Outputs

### Trained Model (`trained_model.pkl`)
- **Best Model**: GradientBoosting (R² = 0.9995, F1 = 1.0)
- **Architecture**: Hybrid regression (Heat Score 0-100) + classification (Low/Moderate/High/Extreme)
- **Top Features**: UHI_Intensity, Anthropogenic_Heat, Building_Density, Impervious_Frac

### Heat Score Engineering
```
HeatScore = 0.40 × LST_norm + 0.25 × UHI_norm + 0.15 × UTFVI_norm
          + 0.10 × Anthropogenic_Heat_norm + 0.10 × Impervious_norm
```
Based on Urban Heat Vulnerability Index (Inostroza et al., 2016).

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Project Overview](docs/Project_Overview.md) | Problem statement, scientific approach |
| [Data Sources](docs/Data_Sources.md) | All datasets with citations |
| [Feature Definitions](docs/Feature_Definitions.md) | Data dictionary with formulas |
| [Processing Workflow](docs/Processing_Workflow.md) | Pipeline steps with diagrams |
| [Dataset Metadata](docs/Dataset_Metadata.md) | Spatial/temporal resolution details |
| [Architecture](docs/Architecture.md) | System design and module dependencies |

---

## 🔮 Roadmap

- [x] Phase 1: Data Collection & Preprocessing Pipeline (GEE)
- [x] Phase 2: ML Model Training (6 ensemble models with RFECV + SHAP)
- [x] Phase 3: UHI Hotspot Classification & Severity Mapping
- [x] Phase 4: Cooling Intervention Recommendations (NSGA-II Optimization)
- [x] Phase 5: Interactive Web Dashboard (Scenario Simulator)

---

## 📝 License

Built for the ISRO Bharatiya Antariksh Hackathon. Research use only.
