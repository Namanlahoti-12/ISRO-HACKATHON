"""
generate_raster.py - Dense Raster Prediction Pipeline
======================================================
Reads GeoTIFF feature rasters exported from Google Earth Engine,
stacks them into a feature array, runs the trained GradientBoostingRegressor
pixel-by-pixel, and outputs predicted_heatscore.tif + per-feature COGs.

Usage:
    python generate_raster.py          # Uses defaults
    python generate_raster.py --force  # Regenerate even if output exists
"""

import os
import sys
import time
import pickle
import argparse

import numpy as np
import pandas as pd


try:
    import rasterio
    from rasterio.transform import from_bounds
except ImportError:
    print('[FATAL] rasterio is required: pip install rasterio')
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW_RASTER_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw', 'rasters')
MODEL_PATH     = os.path.join(PROJECT_ROOT, 'models', 'output', 'trained_model.pkl')
OUTPUT_DIR     = os.path.join(PROJECT_ROOT, 'outputs', 'rasters')


def _has_tifs(path):
    return os.path.isdir(path) and any(
        name.lower().endswith('.tif') for name in os.listdir(path)
    )


def _input_raster_dir():
    if _has_tifs(RAW_RASTER_DIR):
        return RAW_RASTER_DIR
    if _has_tifs(OUTPUT_DIR):
        return OUTPUT_DIR
    return RAW_RASTER_DIR

# Colour ramps for individual feature layers (name -> (vmin, vmax, cmap_name))
# These are used to pre-render coloured PNGs for each feature layer.
LAYER_COLOUR_RAMPS = {
    'HeatScore_Predicted': (0, 100, 'hot_r'),
    'LST':                 (20, 55, 'hot_r'),
    'AirTemp':             (25, 45, 'hot_r'),
    'NDVI':                (-0.1, 0.8, 'RdYlGn'),
    'NDBI':                (-0.3, 0.35, 'RdYlGn_r'),
    'NDWI':                (-0.5, 0.6, 'RdYlBu'),
    'MNDWI':               (-0.6, 0.7, 'RdYlBu'),
    'Population_Density':  (0, 500, 'YlOrRd'),
    'Building_Density':    (0, 90, 'YlOrRd'),
    'Building_Height':     (0, 30, 'YlOrRd'),
    'Road_Density_Proxy':  (0, 1, 'YlOrRd'),
    'Nighttime_Lights':    (0, 63, 'inferno'),
    'Impervious_Frac':     (0, 1, 'YlOrRd'),
    'Tree_Cover_Pct':      (0, 80, 'YlGn'),
    'Dist_Water':          (0, 10000, 'YlGnBu_r'),
    'Dist_Green':          (0, 5000, 'RdYlGn_r'),
    'Green_Space_Density': (0, 1, 'YlGn'),
    'Albedo':              (0.05, 0.4, 'RdYlBu'),
    'Humidity':            (20, 70, 'YlGnBu'),
    'WindSpeed':           (0, 6, 'Blues'),
    'WindDirection':       (0, 360, 'hsv'),
    'SolarRadiation':      (0, 1000, 'YlOrRd'),
    'Elevation':           (150, 350, 'terrain'),
    'Slope':               (0, 15, 'YlOrBr'),
    'UHI_Intensity':       (-5, 10, 'hot_r'),
    'UTFVI':               (-1, 1, 'RdYlGn_r'),
    'Anthropogenic_Heat':  (0, 1, 'YlOrRd'),
    'LULC_ESA':            (10, 80, 'Set3'),
    'LULC_DW':             (0, 7, 'Set3'),
    'SAVI':                (-0.1, 0.8, 'RdYlGn'),
    'Building_Volume':     (0, 500, 'YlOrRd'),
    'Surface_Roughness':   (0, 1, 'YlOrBr'),
}


def load_model():
    """Load the trained model bundle."""
    if not os.path.exists(MODEL_PATH):
        print(f'[FATAL] Model not found: {MODEL_PATH}')
        sys.exit(1)
    with open(MODEL_PATH, 'rb') as f:
        bundle = pickle.load(f)
    print(f'[OK] Model loaded: {bundle["best_model_name"]}')
    print(f'[OK] Features ({len(bundle["feature_columns"])}): {bundle["feature_columns"]}')
    return bundle


def load_raster(path):
    """Load a single-band GeoTIFF and return (data, profile)."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
    return data, profile, transform, crs, bounds


def generate_predicted_heatscore(bundle, force=False):
    """
    Stack feature rasters, run AI inference, write predicted_heatscore.tif.
    Returns the path to the output file and raster metadata.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, 'HeatScore_Predicted.tif')

    if os.path.exists(out_path) and not force:
        print(f'[OK] HeatScore_Predicted.tif already exists (use --force to regenerate)')
        with rasterio.open(out_path) as src:
            return out_path, src.profile.copy(), src.bounds

    feature_cols = bundle['feature_columns']
    reg_model = bundle['regression_model']
    raster_dir = _input_raster_dir()

    # Load reference raster for CRS/transform
    ref_path = os.path.join(raster_dir, f'{feature_cols[0]}.tif')
    ref_data, ref_profile, ref_transform, ref_crs, ref_bounds = load_raster(ref_path)
    height, width = ref_data.shape

    print(f'[OK] Raster grid: {width} x {height} = {width * height} pixels')
    print(f'[OK] Bounds: {ref_bounds}')
    print(f'[OK] CRS: {ref_crs}')

    # Stack feature rasters
    t0 = time.time()
    stack = np.full((len(feature_cols), height, width), np.nan, dtype=np.float32)
    for i, feat in enumerate(feature_cols):
        feat_path = os.path.join(raster_dir, f'{feat}.tif')
        if not os.path.exists(feat_path):
            print(f'[WARN] Missing raster for feature: {feat}')
            continue
        data, _, _, _, _ = load_raster(feat_path)
        if data.shape != (height, width):
            print(f'[WARN] Shape mismatch for {feat}: expected {(height, width)}, got {data.shape}')
            continue
        stack[i] = data
        print(f'  Loaded: {feat}.tif  min={np.nanmin(data):.4f}  max={np.nanmax(data):.4f}')

    # Flatten to (N_pixels, N_features)
    flat = stack.reshape(len(feature_cols), -1).T  # (H*W, N_features)

    # Create valid mask (pixels where ALL features have data)
    valid_mask = ~np.isnan(flat).any(axis=1)
    n_valid = valid_mask.sum()
    print(f'[OK] Valid pixels: {n_valid} / {height * width}')

    if n_valid == 0:
        print('[FATAL] No valid pixels found. Check raster alignment.')
        sys.exit(1)

    # Run AI inference
    t1 = time.time()
    predictions = np.full(height * width, np.nan, dtype=np.float32)
    predictions[valid_mask] = reg_model.predict(flat[valid_mask]).astype(np.float32)
    predictions[valid_mask] = np.clip(predictions[valid_mask], 0, 100)
    t2 = time.time()

    print(f'[OK] Inference complete: {t2 - t1:.2f}s')
    print(f'[OK] Predictions: min={np.nanmin(predictions):.2f}, max={np.nanmax(predictions):.2f}, mean={np.nanmean(predictions):.2f}')

    # Write output GeoTIFF
    result = predictions.reshape(height, width)
    out_profile = ref_profile.copy()
    out_profile.update(
        dtype='float32',
        count=1,
        compress='deflate',
        nodata=np.nan,
    )

    with rasterio.open(out_path, 'w', **out_profile) as dst:
        dst.write(result, 1)
        dst.update_tags(
            LAYER_NAME='HeatScore_Predicted',
            MODEL=bundle['best_model_name'],
            FEATURES=','.join(feature_cols),
        )

    t3 = time.time()
    print(f'[OK] Written: {out_path} ({os.path.getsize(out_path)} bytes, {t3 - t0:.2f}s total)')

    return out_path, out_profile, ref_bounds


def generate_simulated_raster(interventions):
    """
    Apply interventions to the raster stack, run AI inference, 
    and write HeatScore_Predicted_simulated.tif and HeatScore_Predicted_diff.tif.
    """
    from cooling_engine.feature_modifier import FeatureModifier
    modifier = FeatureModifier()

    bundle = load_model()
    feature_cols = bundle['feature_columns']
    reg_model = bundle['regression_model']
    raster_dir = _input_raster_dir()

    ref_path = os.path.join(raster_dir, f'{feature_cols[0]}.tif')
    ref_data, ref_profile, ref_transform, ref_crs, ref_bounds = load_raster(ref_path)
    height, width = ref_data.shape

    stack = np.full((len(feature_cols), height, width), np.nan, dtype=np.float32)
    for i, feat in enumerate(feature_cols):
        feat_path = os.path.join(raster_dir, f'{feat}.tif')
        if os.path.exists(feat_path):
            data, _, _, _, _ = load_raster(feat_path)
            if data.shape == (height, width):
                stack[i] = data

    flat = stack.reshape(len(feature_cols), -1).T
    valid_mask = ~np.isnan(flat).any(axis=1)
    
    if valid_mask.sum() == 0:
        return None

    # Original predictions (baseline)
    baseline_predictions = reg_model.predict(flat[valid_mask]).astype(np.float32)
    baseline_predictions = np.clip(baseline_predictions, 0, 100)

    # Convert to DataFrame for feature modifier
    df = pd.DataFrame(flat[valid_mask], columns=feature_cols)
    modified_df = modifier.apply_to_dataframe_vectorized(df, interventions)
    
    # Fill NA and predict
    X_mod = modified_df[feature_cols].fillna(0)
    sim_predictions = reg_model.predict(X_mod).astype(np.float32)
    sim_predictions = np.clip(sim_predictions, 0, 100)

    diff_predictions = baseline_predictions - sim_predictions

    # Write simulated raster
    sim_result = np.full(height * width, np.nan, dtype=np.float32)
    sim_result[valid_mask] = sim_predictions
    sim_result = sim_result.reshape(height, width)

    diff_result = np.full(height * width, np.nan, dtype=np.float32)
    diff_result[valid_mask] = diff_predictions
    diff_result = diff_result.reshape(height, width)

    out_profile = ref_profile.copy()
    out_profile.update(dtype='float32', count=1, compress='deflate', nodata=np.nan)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sim_path = os.path.join(OUTPUT_DIR, 'HeatScore_Predicted_simulated.tif')
    diff_path = os.path.join(OUTPUT_DIR, 'HeatScore_Predicted_diff.tif')

    with rasterio.open(sim_path, 'w', **out_profile) as dst:
        dst.write(sim_result, 1)
        dst.update_tags(LAYER_NAME='HeatScore_Predicted_simulated')

    with rasterio.open(diff_path, 'w', **out_profile) as dst:
        dst.write(diff_result, 1)
        dst.update_tags(LAYER_NAME='HeatScore_Predicted_diff')

    return {
        'sim_path': sim_path,
        'diff_path': diff_path,
        'before_mean': float(np.mean(baseline_predictions)),
        'after_mean': float(np.mean(sim_predictions)),
        'reduction': float(np.mean(diff_predictions)),
    }


def copy_feature_rasters_to_output(force=False):
    """
    Copy individual feature rasters to outputs/rasters/ so the tile server
    can serve them alongside the predicted HeatScore.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raster_dir = _input_raster_dir()
    if os.path.abspath(raster_dir) == os.path.abspath(OUTPUT_DIR):
        print(f'[OK] Serving precomputed rasters from {OUTPUT_DIR}')
        return

    copied = 0
    for name in os.listdir(raster_dir):
        if not name.endswith('.tif'):
            continue
        src_path = os.path.join(raster_dir, name)
        dst_path = os.path.join(OUTPUT_DIR, name)
        if os.path.exists(dst_path) and not force:
            continue
        # Just create a symlink or copy
        import shutil
        shutil.copy2(src_path, dst_path)
        copied += 1
    if copied:
        print(f'[OK] Copied {copied} feature rasters to {OUTPUT_DIR}')


def generate_all(force=False):
    """Main entry point: generate HeatScore prediction + copy features."""
    bundle = load_model()

    # Generate predicted heatscore
    out_path, profile, bounds = generate_predicted_heatscore(bundle, force=force)

    # Copy feature rasters for tile serving
    copy_feature_rasters_to_output(force=force)

    # Return metadata for the tile server
    return {
        'heatscore_path': out_path,
        'raster_dir': OUTPUT_DIR,
        'bounds': {
            'west': bounds.left,
            'south': bounds.bottom,
            'east': bounds.right,
            'north': bounds.top,
        },
        'width': profile['width'],
        'height': profile['height'],
        'crs': str(profile.get('crs', 'EPSG:4326')),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate raster predictions')
    parser.add_argument('--force', action='store_true', help='Force regeneration')
    args = parser.parse_args()
    result = generate_all(force=args.force)
    print('\n[DONE] Raster pipeline complete')
    print(f'  Output dir: {OUTPUT_DIR}')
    print(f'  Bounds: {result["bounds"]}')
    print(f'  Grid: {result["width"]} x {result["height"]}')
