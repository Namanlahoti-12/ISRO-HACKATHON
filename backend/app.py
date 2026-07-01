"""
Urban Cooling API — Flask Backend for Scenario Simulator
==========================================================
Provides REST API endpoints for the interactive dashboard:
  - /api/predict — Run scenario predictions in real-time
  - /api/interventions — Get intervention library
  - /api/hotspots — Get hotspot data
  - /api/results — Get optimization results
  - /api/health — Health check

Usage:
    python app.py
    # Server starts at http://localhost:5000
"""

import json
import os
import pickle
import sys
import traceback
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from cooling_engine.feature_modifier import FeatureModifier
from cooling_engine.intervention_library import (
    get_all_interventions, get_category_summary,
    get_feature_to_interventions_map
)

# Serve from Vite dist/ when available, else legacy frontend/
_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
_legacy = os.path.join(os.path.dirname(__file__), '..', 'frontend')
_static = _dist if os.path.isdir(_dist) else _legacy

app = Flask(__name__, static_folder=_static, static_url_path='')
CORS(app)

# =============================================================================
# GLOBAL STATE (loaded once at startup)
# =============================================================================

MODEL_BUNDLE = None
REG_MODEL = None
CLS_MODEL = None
FEATURE_COLUMNS = None
HEAT_CLASSES = None
DATASET = None
HOTSPOTS = None
PREDICTION_GEOJSON = None   # Generated FeatureCollection served as prediction_grid.geojson
GRID_STATS = None            # Per-column min/max/mean/std for color scaling
MODIFIER = FeatureModifier()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')


def load_resources(register_routes=True):
    """Load model, dataset, generate grid GeoJSON, and setup rasters."""
    global REG_MODEL, CLS_MODEL, DATASET, HOTSPOTS, FEATURE_COLUMNS, PREDICTION_GEOJSON
    global RASTER_META, GRID_STATS, HEAT_CLASSES

    print('\n[APP] Loading engine resources...')
    
    # --- ML Model ---
    try:
        with open(os.path.join(PROJECT_ROOT, 'models', 'output', 'trained_model.pkl'), 'rb') as f:
            global MODEL_BUNDLE
            MODEL_BUNDLE = pickle.load(f)
            REG_MODEL = MODEL_BUNDLE['regression_model']
            CLS_MODEL = MODEL_BUNDLE['classification_model']
            FEATURE_COLUMNS = MODEL_BUNDLE['feature_columns']
            HEAT_CLASSES = MODEL_BUNDLE['heat_classes']
            print(f"[OK] Model loaded: {MODEL_BUNDLE['best_model_name']}")
    except Exception as e:
        print(f"[WARN] Failed to load model: {e}")

    # --- Dataset ---
    dataset_path = os.path.join(PROJECT_ROOT, 'data', 'processed', 'master_dataset.csv')
    try:
        DATASET = pd.read_csv(dataset_path)
        print(f"[OK] Dataset loaded: {len(DATASET)} rows")
        
        # Run predictions
        if REG_MODEL is not None:
            X = DATASET[FEATURE_COLUMNS].fillna(0)
            DATASET['HeatScore_Predicted'] = REG_MODEL.predict(X).clip(0, 100).round(2)
            DATASET['HeatClass_Predicted'] = CLS_MODEL.predict(X)
            DATASET['HeatClass_Label'] = DATASET['HeatClass_Predicted'].map(
                {i: name for i, name in enumerate(HEAT_CLASSES)}
            )
            # Extract hotspots
            HOTSPOTS = DATASET[DATASET['HeatClass_Predicted'] >= 2].copy()
            print(f"[OK] Hotspots detected: {len(HOTSPOTS)}")
        
        generate_prediction_geojson()
        
    except Exception as e:
        print(f"[WARN] Failed to load dataset: {e}")

    # --- Generate Raster Pipeline ---
    try:
        from tile_server import register_tile_routes
        
        demo_dir = os.path.join(PROJECT_ROOT, 'outputs', 'demo_rasters')
        if os.path.exists(demo_dir) and len(os.listdir(demo_dir)) > 0:
            print("[APP] DEMO MODE DETECTED. Using synthetic country-wide rasters.")
            raster_meta = {
                'raster_dir': demo_dir,
                'width': 1000,
                'height': 1000,
                'bounds': {'north': 35.5, 'south': 6.7, 'east': 97.4, 'west': 68.1}
            }
        else:
            from generate_raster import generate_all
            raster_meta = generate_all(force=False)
            
        RASTER_META = raster_meta
        print(f"[OK] Raster pipeline ready: {raster_meta['width']}x{raster_meta['height']}")
        
        if register_routes:
            register_tile_routes(app, raster_meta['raster_dir'])
            print(f"[OK] Tile server registered at /api/tiles/<layer>/<z>/<x>/<y>.png")
        
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[WARN] Raster pipeline failed: {e}")


# =============================================================================
# GEOJSON PREDICTION GRID GENERATION
# =============================================================================

COMPUTED_CELL_SIZE_DEG = 0.00027  # Updated at startup by generate_prediction_geojson

# Columns to embed in each GeoJSON feature
GEOJSON_COLUMNS = [
    'PixelID', 'HeatScore_Predicted', 'HeatClass_Label',
    'LST', 'NDVI', 'NDBI', 'NDWI', 'MNDWI',
    'Population_Density', 'Building_Density', 'Building_Height',
    'Road_Density_Proxy', 'Nighttime_Lights',
    'WindSpeed', 'WindDirection', 'Humidity',
    'SolarRadiation', 'UHI_Intensity', 'UTFVI',
    'Albedo', 'Impervious_Frac', 'Tree_Cover_Pct',
    'AirTemp', 'Elevation', 'Slope',
    'Anthropogenic_Heat', 'Dist_Water', 'Dist_Green',
    'Green_Space_Density', 'UTCI_Approx', 'LULC_Derived',
]


def generate_prediction_geojson():
    """
    Convert AI model predictions into a proper GeoJSON FeatureCollection.
    Each feature is a 30 m × 30 m Polygon representing one satellite pixel.
    Saves to outputs/prediction_grid.geojson and caches in PREDICTION_GEOJSON.
    """
    global PREDICTION_GEOJSON, GRID_STATS, COMPUTED_CELL_SIZE_DEG
    if DATASET is None:
        print('[WARN] Cannot generate GeoJSON — dataset not loaded')
        return

    df = DATASET.copy()

    # ---- Compute actual grid cell size from spatial density ----
    try:
        from scipy.spatial import cKDTree
        coords = df[['Latitude', 'Longitude']].values
        tree = cKDTree(coords)
        dists, _ = tree.query(coords, k=2)
        nn_dists = dists[:, 1]  # nearest-neighbor distances
        cell_deg = float(np.median(nn_dists)) * 1.05  # slight overlap
        COMPUTED_CELL_SIZE_DEG = cell_deg
        print(f'[OK] Auto cell size: {cell_deg:.6f} deg (~{cell_deg*111000:.0f} m)')
    except ImportError:
        cell_deg = 0.0035  # fallback ~390m
        COMPUTED_CELL_SIZE_DEG = cell_deg
        print(f'[OK] Fallback cell size: {cell_deg} deg (scipy not available)')

    half_lat = cell_deg / 2
    half_lng = half_lat / np.cos(np.radians(float(df['Latitude'].mean())))

    # ── Derived LULC from spectral indices (0=Veg, 1=Built, 2=Water, 3=Bare)
    if all(c in df.columns for c in ['NDVI', 'NDWI', 'NDBI']):
        lulc = np.where(df['NDWI'] > 0.1,  2,
               np.where(df['NDVI'] > 0.25,  0,
               np.where((df['NDBI'] > 0.0) | (df['NDVI'] < 0.05), 1,
               3))).astype(float)
        df['LULC_Derived'] = lulc

    # ── Compute per-column stats for color scaling ──
    stat_cols = [c for c in GEOJSON_COLUMNS
                 if c in df.columns and c not in
                 ('PixelID', 'HeatClass_Label', 'HeatClass_Predicted')]
    stats = {}
    for col in stat_cols:
        vals = df[col].dropna()
        if len(vals) == 0:
            continue
        stats[col] = {
            'min':  round(float(vals.min()),  6),
            'max':  round(float(vals.max()),  6),
            'mean': round(float(vals.mean()), 6),
            'std':  round(float(vals.std()),  6),
        }
    GRID_STATS = stats

    # ── Build GeoJSON features ──
    features = []
    for _, row in df.iterrows():
        lat = float(row['Latitude'])
        lng = float(row['Longitude'])

        # 30 m × 30 m bounding-box polygon
        coords = [[
            [lng - half_lng, lat - half_lat],
            [lng + half_lng, lat - half_lat],
            [lng + half_lng, lat + half_lat],
            [lng - half_lng, lat + half_lat],
            [lng - half_lng, lat - half_lat],
        ]]

        # Collect all desired properties
        props = {}
        for col in GEOJSON_COLUMNS:
            if col not in row.index:
                continue
            val = row[col]
            if pd.isna(val):
                props[col] = None
            elif isinstance(val, (np.integer,)):
                props[col] = int(val)
            elif isinstance(val, (float, np.floating)):
                props[col] = round(float(val), 6)
            else:
                props[col] = val

        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Polygon', 'coordinates': coords},
            'properties': props,
        })

    geojson = {
        'type': 'FeatureCollection',
        'name': 'prediction_grid',
        'features': features,
    }
    PREDICTION_GEOJSON = geojson

    # ── Persist to disk ──
    out_dir = os.path.join(PROJECT_ROOT, 'outputs')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'prediction_grid.geojson')
    with open(out_path, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))   # compact JSON
    print(f'[OK] prediction_grid.geojson -> {len(features)} polygons saved to {out_path}')


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=''):
    """Serve the React SPA — returns index.html for all non-API paths."""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'model_loaded': MODEL_BUNDLE is not None,
        'dataset_loaded': DATASET is not None,
        'hotspots_detected': len(HOTSPOTS) if HOTSPOTS is not None else 0,
        'model_name': MODEL_BUNDLE['best_model_name'] if MODEL_BUNDLE else None,
        'n_features': len(FEATURE_COLUMNS) if FEATURE_COLUMNS else 0,
    })


@app.route('/api/predict', methods=['POST'])
def predict_scenario():
    """
    Run a scenario prediction with custom intervention parameters.

    Expected JSON body:
    {
        "tree_cover_pct": 20,
        "cool_roof_pct": 40,
        "green_roof_pct": 10,
        "water_body_pct": 5,
        "albedo_change": 0.1,
        "impervious_reduction_pct": 15,
        "building_density_reduction_pct": 10
    }
    """
    if HOTSPOTS is None or REG_MODEL is None:
        return jsonify({'error': 'Model or data not loaded'}), 500

    try:
        params = request.get_json(force=True)

        # Generate intervention list from scenario params
        interventions = FeatureModifier.generate_scenario(
            tree_cover_pct=float(params.get('tree_cover_pct', 0)),
            cool_roof_pct=float(params.get('cool_roof_pct', 0)),
            green_roof_pct=float(params.get('green_roof_pct', 0)),
            water_body_pct=float(params.get('water_body_pct', 0)),
            albedo_change=float(params.get('albedo_change', 0)),
            impervious_reduction_pct=float(params.get('impervious_reduction_pct', 0)),
            building_density_reduction_pct=float(params.get('building_density_reduction_pct', 0)),
        )

        if not interventions:
            before_mean = float(HOTSPOTS['HeatScore_Predicted'].mean())
            return jsonify({
                'before_mean': round(before_mean, 2),
                'after_mean': round(before_mean, 2),
                'reduction': 0.0,
                'reduction_pct': 0.0,
                'before_max': round(float(HOTSPOTS['HeatScore_Predicted'].max()), 2),
                'after_max': round(float(HOTSPOTS['HeatScore_Predicted'].max()), 2),
                'interventions_applied': [],
                'class_distribution_before': _get_class_distribution(HOTSPOTS),
                'class_distribution_after': _get_class_distribution(HOTSPOTS),
            })

        # Apply interventions
        modified = MODIFIER.apply_to_dataframe_vectorized(HOTSPOTS, interventions)

        # Re-predict
        X_mod = modified[FEATURE_COLUMNS].fillna(0)
        modified['HeatScore_Predicted'] = REG_MODEL.predict(X_mod).clip(0, 100).round(2)
        modified['HeatClass_Predicted'] = CLS_MODEL.predict(X_mod)
        modified['HeatClass_Label'] = modified['HeatClass_Predicted'].map(
            {i: name for i, name in enumerate(HEAT_CLASSES)}
        )

        before_mean = float(HOTSPOTS['HeatScore_Predicted'].mean())
        after_mean = float(modified['HeatScore_Predicted'].mean())
        reduction = before_mean - after_mean

        result = {
            'before_mean': round(before_mean, 2),
            'after_mean': round(after_mean, 2),
            'reduction': round(reduction, 2),
            'reduction_pct': round(reduction / before_mean * 100, 1) if before_mean > 0 else 0,
            'before_max': round(float(HOTSPOTS['HeatScore_Predicted'].max()), 2),
            'after_max': round(float(modified['HeatScore_Predicted'].max()), 2),
            'before_min': round(float(HOTSPOTS['HeatScore_Predicted'].min()), 2),
            'after_min': round(float(modified['HeatScore_Predicted'].min()), 2),
            'n_hotspots': len(HOTSPOTS),
            'interventions_applied': [
                {'id': s['id'], 'coverage': s['coverage']}
                for s in interventions
            ],
            'class_distribution_before': _get_class_distribution(HOTSPOTS),
            'class_distribution_after': _get_class_distribution(modified),
            'feature_changes': _get_feature_changes(HOTSPOTS, modified),
        }

        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/interventions')
def get_interventions():
    """Get the complete intervention library."""
    library = get_all_interventions()
    summary = get_category_summary()
    feature_map = get_feature_to_interventions_map()

    result = {
        'total': len(library),
        'categories': summary,
        'feature_map': feature_map,
        'interventions': {}
    }

    for iid, data in library.items():
        result['interventions'][iid] = {
            'id': data['id'],
            'name': data['name'],
            'category': data['category'],
            'description': data['description'],
            'cooling_potential': data['cooling_potential_celsius'],
            'cost': data['cost_per_unit'],
            'feasibility': data['feasibility_score'],
            'indian_suitability': data.get('indian_suitability', 'medium'),
            'co_benefits': data.get('co_benefits', []),
            'feature_effects': {k: v['value'] for k, v in data['feature_effects'].items()},
        }

    return jsonify(result)


@app.route('/api/hotspots')
def get_hotspots():
    """Get hotspot summary data."""
    if HOTSPOTS is None:
        return jsonify({'error': 'No data loaded'}), 500

    result = {
        'total_pixels': len(DATASET) if DATASET is not None else 0,
        'hotspot_pixels': len(HOTSPOTS),
        'hotspot_pct': round(len(HOTSPOTS) / len(DATASET) * 100, 1) if DATASET is not None else 0,
        'avg_heat_score': round(float(HOTSPOTS['HeatScore_Predicted'].mean()), 2),
        'max_heat_score': round(float(HOTSPOTS['HeatScore_Predicted'].max()), 2),
        'class_distribution': _get_class_distribution(HOTSPOTS),
        'city_stats': {
            'avg_heat_score': round(float(DATASET['HeatScore_Predicted'].mean()), 2),
            'class_distribution': _get_class_distribution(DATASET),
        } if DATASET is not None else {},
    }

    # Key feature summaries
    key_features = ['NDVI', 'NDBI', 'Albedo', 'Impervious_Frac',
                    'Building_Density', 'Population_Density', 'Tree_Cover_Pct',
                    'Dist_Green', 'WindSpeed', 'UHI_Intensity']
    result['feature_summary'] = {}
    for feat in key_features:
        if feat in HOTSPOTS.columns:
            result['feature_summary'][feat] = {
                'hotspot_mean': round(float(HOTSPOTS[feat].mean()), 4),
                'city_mean': round(float(DATASET[feat].mean()), 4) if DATASET is not None and feat in DATASET.columns else None,
            }

    return jsonify(result)


@app.route('/api/results')
def get_results():
    """Get optimization results if available."""
    results_path = os.path.join(PROJECT_ROOT, 'outputs', 'cooling_analysis',
                                'recommendations.json')
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'No optimization results found. Run the engine first.'}), 404


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_class_distribution(df):
    """Get heat class distribution as dict."""
    if 'HeatClass_Label' in df.columns:
        return {
            label: int(count)
            for label, count in df['HeatClass_Label'].value_counts().items()
        }
    return {}


def _get_feature_changes(before_df, after_df):
    """Calculate mean feature changes."""
    changes = {}
    key_features = ['NDVI', 'NDBI', 'Albedo', 'Impervious_Frac',
                    'Building_Density', 'Tree_Cover_Pct', 'WindSpeed',
                    'MNDWI', 'Green_Space_Density', 'Anthropogenic_Heat']
    for feat in key_features:
        if feat in before_df.columns and feat in after_df.columns:
            before_val = float(before_df[feat].mean())
            after_val = float(after_df[feat].mean())
            changes[feat] = {
                'before': round(before_val, 4),
                'after': round(after_val, 4),
                'change': round(after_val - before_val, 4),
                'change_pct': round(
                    (after_val - before_val) / abs(before_val) * 100
                    if before_val != 0 else 0, 1
                ),
            }
    return changes


# =============================================================================
# NEW API ROUTES — Google Maps Dashboard
# =============================================================================

RASTER_META = None   # populated by load_resources -> generate_all

@app.route('/api/config')
def get_config():
    """Return frontend configuration."""
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    center_lat = float(DATASET['Latitude'].mean()) if DATASET is not None else 28.6139
    center_lng = float(DATASET['Longitude'].mean()) if DATASET is not None else 77.2090

    bounds = None
    if RASTER_META:
        bounds = RASTER_META['bounds']
    elif DATASET is not None:
        bounds = {
            'north': float(DATASET['Latitude'].max()),
            'south': float(DATASET['Latitude'].min()),
            'east': float(DATASET['Longitude'].max()),
            'west': float(DATASET['Longitude'].min()),
        }

    return jsonify({
        'maps_api_key': api_key,
        'center': {'lat': center_lat, 'lng': center_lng},
        'zoom': 12,
        'bounds': bounds,
        'total_pixels': RASTER_META['width'] * RASTER_META['height'] if RASTER_META else (len(DATASET) if DATASET is not None else 0),
        'pixel_size_deg': COMPUTED_CELL_SIZE_DEG,
        'model_name': MODEL_BUNDLE['best_model_name'] if MODEL_BUNDLE else None,
        'n_features': len(FEATURE_COLUMNS) if FEATURE_COLUMNS else 0,
        'hotspots': len(HOTSPOTS) if HOTSPOTS is not None else 0,
        'raster_ready': RASTER_META is not None,
        'raster_grid': f'{RASTER_META["width"]}x{RASTER_META["height"]}' if RASTER_META else None,
        'tile_url': '/api/tiles/{layer}/{z}/{x}/{y}.png' if RASTER_META else None,
    })


@app.route('/api/prediction_grid.geojson')
def serve_prediction_geojson():
    """
    Serve the server-generated GeoJSON FeatureCollection.
    Each feature is a 30 m × 30 m Polygon with AI predictions as properties.
    This is the canonical data source for the map overlay.
    """
    if PREDICTION_GEOJSON is None:
        return jsonify({'error': 'GeoJSON not yet generated'}), 503

    from flask import Response
    return Response(
        json.dumps(PREDICTION_GEOJSON, separators=(',', ':')),
        mimetype='application/geo+json',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        },
    )


@app.route('/api/grid_stats')
def serve_grid_stats():
    """
    Return per-column min/max/mean/std statistics.
    Used by the frontend to build MapLibre data-driven color expressions.
    """
    if GRID_STATS is None:
        return jsonify({'error': 'Stats not computed yet'}), 503
    return jsonify(GRID_STATS)


@app.route('/api/grid')
def get_grid():
    """Return all pixel data for map overlay rendering."""
    if DATASET is None:
        return jsonify({'error': 'No data loaded'}), 500

    map_columns = [
        'PixelID', 'Latitude', 'Longitude',
        'HeatScore_Predicted', 'HeatClass_Predicted', 'HeatClass_Label',
        'LST', 'NDVI', 'NDBI', 'NDWI', 'MNDWI',
        'Population_Density', 'Building_Density', 'Road_Density_Proxy',
        'Nighttime_Lights', 'WindSpeed', 'Humidity', 'WindDirection',
        'SolarRadiation', 'UHI_Intensity', 'UTFVI',
        'Albedo', 'Impervious_Frac', 'Tree_Cover_Pct',
        'AirTemp', 'Elevation', 'Slope', 'Anthropogenic_Heat',
        'Building_Height', 'Dist_Water', 'Dist_Green',
        'Green_Space_Density', 'UTCI_Approx',
    ]

    available = [c for c in map_columns if c in DATASET.columns]
    grid_df = DATASET[available].copy()

    # ── Derive LULC from spectral indices (vectorized) ──
    # 0=Vegetation, 1=Built-up, 2=Water, 3=Bare/Other
    if all(c in grid_df.columns for c in ['NDVI', 'NDWI', 'NDBI']):
        ndvi = grid_df['NDVI'].values
        ndwi = grid_df['NDWI'].values
        ndbi = grid_df['NDBI'].values
        lulc = np.where(ndwi > 0.1, 2,          # Water
               np.where(ndvi > 0.25, 0,          # Vegetation
               np.where((ndbi > 0.0) | (ndvi < 0.05), 1,  # Built-up
               3))).astype(float)               # Bare/Mixed
        grid_df['LULC_Derived'] = lulc
        available.append('LULC_Derived')

    # Pre-compute stats for color scaling
    stat_cols = [c for c in available
                 if c not in ('PixelID', 'Latitude', 'Longitude',
                               'HeatClass_Label', 'HeatClass_Predicted')]
    stats = {}
    for col in stat_cols:
        col_vals = grid_df[col].dropna()
        if len(col_vals) == 0:
            continue
        stats[col] = {
            'min': round(float(col_vals.min()), 4),
            'max': round(float(col_vals.max()), 4),
            'mean': round(float(col_vals.mean()), 4),
            'std': round(float(col_vals.std()), 4),
        }

    return jsonify({
        'columns': available,
        'pixels': json.loads(grid_df.fillna(0).round(4).to_json(orient='records')),
        'stats': stats,
    })


@app.route('/api/pixel/<int:pixel_id>')
def get_pixel_detail(pixel_id):
    """Detailed per-pixel data with feature importance contributions."""
    if DATASET is None or REG_MODEL is None:
        return jsonify({'error': 'Data not loaded'}), 500

    pixel = DATASET[DATASET['PixelID'] == pixel_id]
    if pixel.empty:
        return jsonify({'error': f'Pixel {pixel_id} not found'}), 404

    row = pixel.iloc[0]

    # Feature values
    feature_vals = {}
    for col in FEATURE_COLUMNS:
        if col in row.index:
            feature_vals[col] = round(float(row[col]), 4)

    # Approximate per-pixel contributions using
    # feature_importance * (value - mean) as SHAP proxy
    importances = REG_MODEL.feature_importances_
    feature_means = DATASET[FEATURE_COLUMNS].mean()

    contributions = {}
    total_abs = 0
    for i, col in enumerate(FEATURE_COLUMNS):
        deviation = float(row[col]) - float(feature_means[col])
        contrib = float(importances[i]) * deviation
        contributions[col] = round(contrib, 6)
        total_abs += abs(contrib)

    contrib_pct = {}
    if total_abs > 0:
        # Signed percentage keeps the SHAP direction visible in the frontend.
        contrib_pct = {k: round(v / total_abs * 100, 1)
                       for k, v in contributions.items()}

    sorted_contribs = sorted(contrib_pct.items(),
                             key=lambda x: abs(x[1]), reverse=True)

    # Top heat drivers
    top_drivers = []
    for feat, pct in sorted_contribs[:6]:
        pct_abs = abs(pct)
        if pct_abs < 1:
            break
        top_drivers.append({
            'feature': feat,
            'contribution_pct': pct_abs,
            'direction': 'heating' if contributions[feat] > 0 else 'cooling',
            'value': feature_vals.get(feat, 0),
        })

    heat_class = str(row.get('HeatClass_Label', 'Unknown'))
    recommendation = _generate_pixel_recommendation(
        heat_class, feature_vals, contributions)

    # Predicted reduction from optimization
    predicted_reduction = 0.0
    cost_estimate = 0
    results_path = os.path.join(PROJECT_ROOT, 'outputs', 'cooling_analysis',
                                'recommendations.json')
    if os.path.exists(results_path):
        try:
            with open(results_path, 'r') as f:
                opt = json.load(f)
            if 'best_solution' in opt:
                predicted_reduction = opt['best_solution'].get(
                    'predicted_reduction', 0)
                cost_estimate = opt['best_solution'].get('total_cost', 0)
        except Exception:
            pass

    return jsonify({
        'pixel_id': int(pixel_id),
        'latitude': round(float(row['Latitude']), 6),
        'longitude': round(float(row['Longitude']), 6),
        'heat_score': round(float(row.get('HeatScore_Predicted', 0)), 2),
        'lst': round(float(row.get('LST', 0)), 2),
        'air_temp': round(float(row.get('AirTemp', 0)), 2),
        'heat_class': heat_class,
        'features': feature_vals,
        'contributions': dict(sorted_contribs),
        'top_drivers': top_drivers,
        'recommendation': recommendation,
        'predicted_reduction': round(predicted_reduction, 2),
        'cost_estimate': round(cost_estimate, 0),
        'priority': 'Critical' if heat_class == 'Extreme' else (
            'High' if heat_class == 'High' else (
                'Medium' if heat_class == 'Moderate' else 'Low')),
        'confidence': 0.95,
    })


@app.route('/api/predict/spatial', methods=['POST'])
def predict_spatial():
    """Per-pixel scenario predictions using raster pipeline."""
    if REG_MODEL is None:
        return jsonify({'error': 'Model not loaded'}), 500

    try:
        params = request.get_json(force=True)

        interventions = FeatureModifier.generate_scenario(
            tree_cover_pct=float(params.get('tree_cover_pct', 0)),
            cool_roof_pct=float(params.get('cool_roof_pct', 0)),
            green_roof_pct=float(params.get('green_roof_pct', 0)),
            water_body_pct=float(params.get('water_body_pct', 0)),
            albedo_change=float(params.get('albedo_change', 0)),
            impervious_reduction_pct=float(params.get('impervious_reduction_pct', 0)),
            building_density_reduction_pct=float(
                params.get('building_density_reduction_pct', 0)),
        )

        if not interventions:
            return jsonify({
                'pixels': [],
                'summary': {
                    'before_mean': 0, 'after_mean': 0, 'reduction': 0, 'reduction_pct': 0,
                },
                'timestamp': int(time.time()),
            })

        from generate_raster import generate_simulated_raster
        res = generate_simulated_raster(interventions)
        
        if not res:
            return jsonify({'error': 'Simulation failed'}), 500

        before_mean = res['before_mean']
        after_mean = res['after_mean']

        return jsonify({
            'pixels': [], # no longer sending 30k elements to client
            'summary': {
                'before_mean': round(before_mean, 2),
                'after_mean': round(after_mean, 2),
                'reduction': round(before_mean - after_mean, 2),
                'reduction_pct': round(
                    (before_mean - after_mean) / before_mean * 100, 1
                ) if before_mean > 0 else 0,
            },
            'timestamp': int(time.time()),
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _generate_pixel_recommendation(heat_class, features, contributions):
    """Generate cooling strategy recommendation for a single pixel."""
    recs = []
    if heat_class == 'Extreme':
        recs.append('CRITICAL: Immediate cooling intervention needed')
    elif heat_class == 'High':
        recs.append('HIGH PRIORITY: Cooling intervention recommended')

    heating = sorted(
        [(k, v) for k, v in contributions.items() if v > 0],
        key=lambda x: abs(x[1]), reverse=True)

    for feat, _ in heating[:3]:
        if feat in ('NDBI', 'Building_Density', 'Impervious_Frac'):
            recs.append('Install cool/green roofs and high-albedo pavements')
        elif feat in ('NDVI', 'Tree_Cover_Pct', 'Green_Space_Density'):
            recs.append('Plant street trees and create pocket parks')
        elif feat == 'Anthropogenic_Heat':
            recs.append('Improve building energy efficiency')
        elif feat == 'Population_Density':
            recs.append('Implement district cooling systems')
        elif feat == 'WindSpeed':
            recs.append('Create wind corridors in urban planning')
        elif feat == 'Albedo':
            recs.append('Apply reflective coatings on surfaces')

    seen = set()
    unique = []
    for r in recs:
        if r not in seen:
            unique.append(r)
            seen.add(r)

    return ' | '.join(unique[:4]) if unique else 'No specific intervention needed'


# =============================================================================
# MAIN
# =============================================================================

@app.route('/api/search_aoi', methods=['POST'])
def search_aoi():
    """Trigger GEE pipeline for a searched location."""
    try:
        params = request.get_json(force=True)
        lat = float(params.get('lat'))
        lng = float(params.get('lng'))
        
        # Simulate backend generating new rasters
        import gee_pipeline
        success = gee_pipeline.run_gee_pipeline(lat, lng)
        
        if success:
            # Reload metadata and bounds so /api/config is accurate
            global RASTER_META, PREDICTION_GEOJSON, DATASET, HOTSPOTS, GRID_STATS
            load_resources(register_routes=False)
            
        return jsonify({
            'success': success,
            'message': 'Earth Engine pipeline triggered for AOI.' if success else 'Earth Engine authentication required.',
            'timestamp': int(time.time()),
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Load all ML models and rasters at module level so Gunicorn can serve them
print("=" * 60)
print("URBAN COOLING API SERVER (INIT)")
print("=" * 60)

try:
    print("[STEP 1] Starting load_resources()")
    load_resources()
    print("[STEP 2] load_resources() completed successfully")
except Exception as e:
    import traceback
    print("!!!!!!!! STARTUP ERROR !!!!!!!!")
    traceback.print_exc()
    raise
if __name__ == '__main__':
    print('\n  Starting Flask dev server...')
    port = int(os.environ.get('PORT', 5000))
    print(f'  Dashboard: http://localhost:{port}')
    print(f'  API docs:  http://localhost:{port}/api/health\n')
    app.run(host='0.0.0.0', port=port, debug=False)

