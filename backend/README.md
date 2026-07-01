# Backend — Urban Cooling API Server

Flask REST API serving the Cooling Scenario Simulator dashboard.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Start the server
python app.py
```

The server starts at **http://localhost:5000** and serves the frontend dashboard.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the Scenario Simulator dashboard |
| `/api/health` | GET | Health check (model status, dataset size) |
| `/api/predict` | POST | Run a cooling scenario prediction |
| `/api/interventions` | GET | Get full intervention library (31 interventions) |
| `/api/hotspots` | GET | Get hotspot summary data |
| `/api/results` | GET | Get optimization results (if engine has been run) |

## Prediction API

**POST** `/api/predict`

```json
{
    "tree_cover_pct": 20,
    "cool_roof_pct": 40,
    "green_roof_pct": 10,
    "water_body_pct": 5,
    "albedo_change": 0.1,
    "impervious_reduction_pct": 15,
    "building_density_reduction_pct": 10
}
```

**Response**:
```json
{
    "before_mean": 50.28,
    "after_mean": 48.15,
    "reduction": 2.13,
    "reduction_pct": 4.2,
    "class_distribution_before": {"High": 468, "Extreme": 466},
    "class_distribution_after": {"Moderate": 50, "High": 450, "Extreme": 434},
    "feature_changes": { ... }
}
```

## Architecture

- Loads `trained_model.pkl` and `master_dataset.csv` once at startup
- Uses `FeatureModifier` to apply physics-based feature changes
- Re-predicts using the trained GradientBoosting model in real-time
- Stateless API — all predictions are independent
