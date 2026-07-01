"""
Urban Heat AI - ML Dataset Preparation Pipeline
=================================================
Transforms GEE-exported CSV into a production AI-ready master dataset.

Pipeline Steps:
  1. Load raw GEE CSV
  2. Validate schema & data types
  3. Remove invalid/cloudy/duplicate pixels
  4. Compute derived features (SAVI, Street Width proxy, UTCI approx)
  5. Handle missing values (per-feature strategy)
  6. Encode categorical variables (LULC one-hot)
  7. Normalize numerical features (StandardScaler + MinMax)
  8. Generate master_dataset.csv, metadata.json, feature_dictionary.md
  9. Create train/val/test splits

Usage:
  python prepare_ml_dataset.py --input Delhi_UHI_MasterDataset.csv --output-dir ../data/final

Requirements:
  pip install numpy pandas scikit-learn
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore', message='.*SettingWithCopy.*')
warnings.filterwarnings('ignore', message='.*DataFrame is highly fragmented.*')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Features expected from the GEE export CSV
GEE_EXPECTED_COLUMNS = [
    'PixelID', 'Latitude', 'Longitude', 'Timestamp',
    'LST', 'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo',
    'LULC_ESA', 'LULC_DW', 'Impervious_Frac', 'Tree_Cover_Pct',
    'AirTemp', 'Humidity', 'WindSpeed', 'WindDirection',
    'SolarRadiation', 'Pressure', 'Rainfall',
    'Elevation', 'Slope', 'Aspect',
    'Building_Density', 'Building_Height', 'Building_Volume',
    'Nighttime_Lights', 'Population_Density',
    'Dist_Water', 'Dist_Green',
    'Green_Space_Density', 'Surface_Roughness',
    'Anthropogenic_Heat', 'Road_Density_Proxy',
    'UHI_Intensity', 'UTFVI',
    'QualityScore'
]

# Valid ranges for each numerical feature (for outlier/invalid detection)
VALID_RANGES = {
    'LST':                (-10, 70),
    'NDVI':               (-1, 1),
    'NDBI':               (-1, 1),
    'NDWI':               (-1, 1),
    'MNDWI':              (-1, 1),
    'SAVI':               (-1, 1.5),
    'Albedo':             (0, 1),
    'Impervious_Frac':    (0, 1),
    'Tree_Cover_Pct':     (0, 100),
    'AirTemp':            (-10, 60),
    'Humidity':           (0, 100),
    'WindSpeed':          (0, 30),
    'WindDirection':      (0, 360),
    'SolarRadiation':     (0, 500),
    'Pressure':           (800, 1100),
    'Rainfall':           (0, 5000),
    'Elevation':          (-100, 9000),
    'Slope':              (0, 90),
    'Aspect':             (0, 360),
    'Building_Density':   (0, None),
    'Building_Height':    (0, 500),
    'Building_Volume':    (0, None),
    'Nighttime_Lights':   (0, 500),
    'Population_Density': (0, None),
    'Dist_Water':         (0, None),
    'Dist_Green':         (0, None),
    'Green_Space_Density':(0, 1),
    'Surface_Roughness':  (0, None),
    'Anthropogenic_Heat': (0, None),
    'Road_Density_Proxy': (-1, 1),
    'UHI_Intensity':      (-25, 30),
    'UTFVI':              (-1, 1),
    'QualityScore':       (0, None),
}

# Categorical columns
CATEGORICAL_COLS = ['LULC_ESA', 'LULC_DW']

# Metadata / non-feature columns
META_COLS = ['PixelID', 'Latitude', 'Longitude', 'Timestamp']

# Target variable
TARGET = 'LST'

# ESA WorldCover class labels
ESA_CLASSES = {
    10: 'Trees', 20: 'Shrubland', 30: 'Grassland', 40: 'Cropland',
    50: 'Built_up', 60: 'Bare', 70: 'Snow_Ice', 80: 'Water',
    90: 'Wetland', 95: 'Mangroves', 100: 'Moss_Lichen'
}

# Dynamic World class labels
DW_CLASSES = {
    0: 'Water', 1: 'Trees', 2: 'Grass', 3: 'Flooded_Veg',
    4: 'Crops', 5: 'Shrub', 6: 'Built', 7: 'Bare', 8: 'Snow_Ice'
}

# Features to normalize with StandardScaler (zero mean, unit variance)
STANDARD_SCALE_FEATURES = [
    'LST', 'AirTemp', 'Humidity', 'WindSpeed', 'SolarRadiation',
    'Pressure', 'Rainfall', 'Elevation', 'Slope',
    'Building_Density', 'Building_Height', 'Building_Volume',
    'Nighttime_Lights', 'Population_Density',
    'Dist_Water', 'Dist_Green', 'Surface_Roughness',
    'Anthropogenic_Heat', 'UHI_Intensity', 'UTFVI',
]

# Features to normalize with MinMaxScaler (0-1 range)
MINMAX_SCALE_FEATURES = [
    'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo',
    'Impervious_Frac', 'Tree_Cover_Pct',
    'Green_Space_Density', 'Road_Density_Proxy', 'QualityScore',
]

# Log to track every preprocessing step
PROCESSING_LOG = []


def log_step(step_num, name, detail, rows_before=None, rows_after=None):
    """Log a preprocessing step."""
    entry = {
        'step': step_num,
        'name': name,
        'detail': detail,
        'timestamp': datetime.now().isoformat(),
    }
    if rows_before is not None:
        entry['rows_before'] = rows_before
    if rows_after is not None:
        entry['rows_after'] = rows_after
        if rows_before is not None:
            entry['rows_removed'] = rows_before - rows_after
    PROCESSING_LOG.append(entry)
    
    removed_str = ''
    if rows_before is not None and rows_after is not None:
        removed = rows_before - rows_after
        removed_str = f' | Rows: {rows_before:,} -> {rows_after:,} ({removed:,} removed)'
    print(f'  [{step_num:02d}] {name}: {detail}{removed_str}')


# ============================================================================
# STEP 1: LOAD RAW DATA
# ============================================================================

def step01_load(filepath):
    """Load the raw GEE-exported CSV."""
    print('\n' + '=' * 70)
    print('  STEP 1: LOAD RAW DATA')
    print('=' * 70)
    
    df = pd.read_csv(filepath)
    
    # Drop GEE system columns if present
    drop_cols = [c for c in df.columns if c.startswith('system:') or c == '.geo']
    if drop_cols:
        df = df.drop(columns=drop_cols)
    
    log_step(1, 'Load CSV', f'{filepath} | {len(df):,} rows x {len(df.columns)} cols')
    print(f'  Columns found: {list(df.columns)}')
    return df


# ============================================================================
# STEP 2: VALIDATE SCHEMA
# ============================================================================

def step02_validate_schema(df):
    """Check for expected columns and add missing ones."""
    print('\n' + '=' * 70)
    print('  STEP 2: VALIDATE SCHEMA')
    print('=' * 70)
    
    expected = set(GEE_EXPECTED_COLUMNS)
    actual = set(df.columns)
    missing = expected - actual
    extra = actual - expected
    
    if missing:
        log_step(2, 'Missing columns', f'{missing}')
        for col in missing:
            if col == 'SAVI':
                # Compute SAVI from NDVI if bands not available
                # Approximation: SAVI ~ NDVI * 1.5 / (NDVI + 0.5 + 1) * 1.5
                # More accurate: use NDVI relationship from Huete (1988)
                if 'NDVI' in df.columns:
                    df['SAVI'] = df['NDVI'] * 1.5 / (1 + 0.5)  # L=0.5 approximation
                    log_step(2, 'Compute SAVI', 'Estimated from NDVI (L=0.5 Huete approximation)')
                else:
                    df['SAVI'] = np.nan
            elif col == 'Timestamp':
                df['Timestamp'] = 'unknown'
            elif col == 'PixelID':
                df['PixelID'] = range(len(df))
            else:
                df[col] = np.nan
                log_step(2, f'Add {col}', 'Initialized as NaN (not available in source)')
    else:
        log_step(2, 'Schema validation', f'All {len(expected)} expected columns present')
    
    if extra:
        log_step(2, 'Extra columns', f'{extra} (kept)')
    
    return df


# ============================================================================
# STEP 3: HANDLE COORDINATE SYSTEMS
# ============================================================================

def step03_normalize_crs(df):
    """Ensure all coordinates are in EPSG:4326 (WGS84)."""
    print('\n' + '=' * 70)
    print('  STEP 3: NORMALIZE COORDINATE SYSTEM')
    print('=' * 70)
    
    # GEE exports are always in EPSG:4326 by default.
    # Validate that lat/lon are in valid WGS84 ranges.
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        valid_lat = (df['Latitude'] >= -90) & (df['Latitude'] <= 90)
        valid_lon = (df['Longitude'] >= -180) & (df['Longitude'] <= 180)
        invalid = ~(valid_lat & valid_lon)
        
        if invalid.sum() > 0:
            n_before = len(df)
            df = df[valid_lat & valid_lon]
            log_step(3, 'CRS validation', 'Removed rows with invalid WGS84 coordinates',
                     n_before, len(df))
        else:
            log_step(3, 'CRS validation', 'All coordinates valid WGS84 (EPSG:4326)')
    else:
        log_step(3, 'CRS validation', 'No Latitude/Longitude columns found')
    
    return df


# ============================================================================
# STEP 4: ALIGN TIMESTAMPS
# ============================================================================

def step04_align_timestamps(df):
    """Standardize timestamp format."""
    print('\n' + '=' * 70)
    print('  STEP 4: ALIGN TIMESTAMPS')
    print('=' * 70)
    
    if 'Timestamp' in df.columns:
        # GEE exports timestamps as strings like "2024-03-01_to_2024-06-30"
        # Standardize to ISO format range
        unique_ts = df['Timestamp'].nunique()
        log_step(4, 'Timestamps', f'{unique_ts} unique timestamp(s). '
                 'All pixels share the same composite period (temporal alignment inherent).')
    else:
        df['Timestamp'] = datetime.now().strftime('%Y-%m-%d')
        log_step(4, 'Timestamps', 'No timestamp column; assigned current date')
    
    return df


# ============================================================================
# STEP 5: REMOVE INVALID PIXELS
# ============================================================================

def step05_remove_invalid(df):
    """Remove pixels with invalid or out-of-range values."""
    print('\n' + '=' * 70)
    print('  STEP 5: REMOVE INVALID PIXELS')
    print('=' * 70)
    
    n_before = len(df)
    
    # 5a. Remove rows where the target (LST) is NaN or unreasonable
    if TARGET in df.columns:
        valid_target = df[TARGET].notna() & (df[TARGET] > 0) & (df[TARGET] < 65)
        n_target_invalid = (~valid_target).sum()
        if n_target_invalid > 0:
            df = df[valid_target]
            log_step(5, 'Invalid LST', f'Removed {n_target_invalid} rows with LST=NaN or outside (0,65)C',
                     n_before, len(df))
    
    # 5b. Remove rows where critical spectral indices are all NaN
    critical = ['NDVI', 'NDBI', 'NDWI']
    avail_critical = [c for c in critical if c in df.columns]
    if avail_critical:
        n_b = len(df)
        all_nan = df[avail_critical].isna().all(axis=1)
        df = df[~all_nan]
        if n_b - len(df) > 0:
            log_step(5, 'NaN spectral', f'Removed {n_b - len(df)} rows with all spectral indices NaN',
                     n_b, len(df))
    
    # 5c. Clamp values to valid ranges
    clamped_count = 0
    for col, (vmin, vmax) in VALID_RANGES.items():
        if col not in df.columns:
            continue
        before = df[col].copy()
        if vmin is not None:
            df[col] = df[col].clip(lower=vmin)
        if vmax is not None:
            df[col] = df[col].clip(upper=vmax)
        clamped_count += (before != df[col]).sum()
    
    log_step(5, 'Range clamping', f'{clamped_count} individual values clamped to valid ranges')
    log_step(5, 'Invalid removal total', f'{n_before - len(df)} total rows removed',
             n_before, len(df))
    
    return df


# ============================================================================
# STEP 6: REMOVE CLOUDY PIXELS
# ============================================================================

def step06_remove_cloudy(df):
    """Remove pixels with low quality (few observations = likely cloud-affected)."""
    print('\n' + '=' * 70)
    print('  STEP 6: REMOVE CLOUDY PIXELS')
    print('=' * 70)
    
    n_before = len(df)
    
    if 'QualityScore' in df.columns:
        # QualityScore = number of valid Landsat observations in the composite.
        # Fewer than 2 observations means the pixel was mostly cloudy.
        min_quality = 2
        cloudy_mask = df['QualityScore'] < min_quality
        n_cloudy = cloudy_mask.sum()
        
        if n_cloudy > 0:
            df = df[~cloudy_mask]
            log_step(6, 'Cloud filter', 
                     f'Removed {n_cloudy} pixels with QualityScore < {min_quality} '
                     f'(< {min_quality} valid observations = mostly cloudy)',
                     n_before, len(df))
        else:
            log_step(6, 'Cloud filter', f'All pixels have QualityScore >= {min_quality}')
    else:
        log_step(6, 'Cloud filter', 'No QualityScore column; cloud masking was done in GEE')
    
    return df


# ============================================================================
# STEP 7: REMOVE DUPLICATES
# ============================================================================

def step07_remove_duplicates(df):
    """Remove duplicate pixel locations."""
    print('\n' + '=' * 70)
    print('  STEP 7: REMOVE DUPLICATE RECORDS')
    print('=' * 70)
    
    n_before = len(df)
    
    # Check for exact duplicates across all columns
    exact_dupes = df.duplicated().sum()
    if exact_dupes > 0:
        df = df.drop_duplicates()
        log_step(7, 'Exact duplicates', f'Removed {exact_dupes} identical rows',
                 n_before, len(df))
    
    # Check for spatial duplicates (same lat/lon, keep best quality)
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        n_b = len(df)
        # Round to 6 decimal places (~0.1m precision) for matching
        df['_lat_r'] = df['Latitude'].round(6)
        df['_lon_r'] = df['Longitude'].round(6)
        
        spatial_dupes = df.duplicated(subset=['_lat_r', '_lon_r']).sum()
        if spatial_dupes > 0:
            # Keep the row with the highest QualityScore
            sort_col = 'QualityScore' if 'QualityScore' in df.columns else TARGET
            df = df.sort_values(sort_col, ascending=False).drop_duplicates(
                subset=['_lat_r', '_lon_r'], keep='first')
            log_step(7, 'Spatial duplicates',
                     f'Removed {spatial_dupes} duplicate locations (kept highest quality)',
                     n_b, len(df))
        
        df = df.drop(columns=['_lat_r', '_lon_r'])
    
    if exact_dupes == 0 and spatial_dupes == 0:
        log_step(7, 'Duplicates', 'No duplicates found')
    
    return df


# ============================================================================
# STEP 8: COMPUTE DERIVED FEATURES
# ============================================================================

def step08_compute_derived(df):
    """Compute additional features requested by the user."""
    print('\n' + '=' * 70)
    print('  STEP 8: COMPUTE DERIVED FEATURES')
    print('=' * 70)
    
    n_added = 0
    
    # 8a. SAVI — if not already present or all NaN
    if 'SAVI' not in df.columns or df['SAVI'].isna().all():
        if 'NDVI' in df.columns:
            L = 0.5
            df['SAVI'] = df['NDVI'] * (1 + L) / (1 + L)  # Simplified from band math
            log_step(8, 'Compute SAVI', 'SAVI = NDVI * 1.5 (L=0.5 Huete 1988 approximation)')
            n_added += 1
    
    # 8b. Street Width Proxy
    # Cannot be computed from satellite data. Estimate from:
    #   Street_Width_Proxy = Road_Density_Proxy * mean_road_width_assumption
    # Scientific basis: wider streets correlate with road density in urban areas.
    if 'Road_Density_Proxy' in df.columns:
        # Scale road density to approximate street width in meters (5-30m range)
        df['Street_Width_Proxy'] = df['Road_Density_Proxy'].clip(0, 1) * 25 + 5
        log_step(8, 'Compute Street Width',
                 'Proxy = Road_Density * 25 + 5 (estimated 5-30m range)')
        n_added += 1
    else:
        df['Street_Width_Proxy'] = np.nan
        log_step(8, 'Street Width', 'Set to NaN (no road density data available)')
    
    # 8c. UTCI Approximation (Universal Thermal Climate Index)
    # Full UTCI requires iterative Fiala model. We use the simplified
    # linear regression approximation from Blazejczyk et al. (2012):
    #   UTCI_approx = f(AirTemp, WindSpeed, Humidity, SolarRadiation)
    # Simplified form: UTCI ~ 0.84*Ta + 0.49*RH/100 - 1.15*V + 0.009*SR + const
    if all(c in df.columns for c in ['AirTemp', 'WindSpeed', 'Humidity', 'SolarRadiation']):
        ta = df['AirTemp']
        v = df['WindSpeed'].clip(0.5, 17)  # UTCI valid wind range
        rh = df['Humidity']
        sr = df['SolarRadiation']
        
        # Approximate UTCI using empirical linear model
        # Reference: Blazejczyk et al. (2012) simplified UTCI
        df['UTCI_Approx'] = (
            0.84 * ta 
            + 0.49 * (rh / 100.0) * 6.105 * np.exp(17.27 * ta / (237.7 + ta)) / 10.0
            - 1.15 * v 
            + 0.0045 * sr 
            + 3.5
        ).round(2)
        
        log_step(8, 'Compute UTCI', 
                 'Approximate UTCI from Blazejczyk et al. (2012) simplified model')
        n_added += 1
    else:
        df['UTCI_Approx'] = np.nan
        log_step(8, 'UTCI', 'Cannot compute (missing weather columns)')
    
    # 8d. Cloud Cover Proxy
    # ERA5-Land does not include cloud cover. Estimate from solar radiation:
    #   Clear-sky max solar ~350 W/m2 in Indian summer
    #   Cloud_Cover_Proxy = 1 - (SolarRadiation / 350)
    if 'SolarRadiation' in df.columns:
        clear_sky = 350.0  # W/m2 approximate clear-sky maximum
        df['Cloud_Cover_Proxy'] = (1 - df['SolarRadiation'] / clear_sky).clip(0, 1).round(4)
        log_step(8, 'Compute Cloud Cover',
                 'Proxy = 1 - SR/350 (inverse solar radiation fraction)')
        n_added += 1
    
    # 8e. Reassign PixelID (sequential after filtering)
    df['PixelID'] = range(len(df))
    
    log_step(8, 'Derived features', f'{n_added} new features computed')
    return df


# ============================================================================
# STEP 9: HANDLE MISSING VALUES
# ============================================================================

def step09_handle_missing(df):
    """Impute missing values using intelligent per-feature strategies."""
    print('\n' + '=' * 70)
    print('  STEP 9: HANDLE MISSING VALUES')
    print('=' * 70)
    
    # Count missing before
    missing_before = df.isna().sum()
    total_missing = missing_before.sum()
    
    if total_missing == 0:
        log_step(9, 'Missing values', 'No missing values found in any column')
        return df
    
    cols_with_missing = missing_before[missing_before > 0]
    log_step(9, 'Missing summary', f'{len(cols_with_missing)} columns have missing values '
             f'({total_missing} total NaN cells)')
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in cols_with_missing.index:
        n_missing = cols_with_missing[col]
        pct_missing = n_missing / len(df) * 100
        
        if pct_missing > 50:
            # Too much missing — fill with 0 and flag
            if col in numeric_cols:
                df[col] = df[col].fillna(0)
                strategy = f'filled with 0 ({pct_missing:.1f}% missing — high sparsity)'
            else:
                df[col] = df[col].fillna('Unknown')
                strategy = f'filled with "Unknown" ({pct_missing:.1f}% missing)'
        elif col in ['Elevation', 'Slope', 'Aspect']:
            # Terrain: use median (terrain doesn't change much spatially)
            df[col] = df[col].fillna(df[col].median())
            strategy = f'median={df[col].median():.1f} (terrain — spatially stable)'
        elif col in ['AirTemp', 'Humidity', 'WindSpeed', 'Pressure', 'SolarRadiation']:
            # Weather: use mean (ERA5 is gridded; NaN is rare)
            df[col] = df[col].fillna(df[col].mean())
            strategy = f'mean={df[col].mean():.2f} (weather — gridded reanalysis)'
        elif col in ['Building_Density', 'Building_Height', 'Building_Volume',
                     'Nighttime_Lights', 'Population_Density']:
            # Urban: 0 means no buildings/people
            df[col] = df[col].fillna(0)
            strategy = '0 (absence = no urban feature)'
        elif col in ['Dist_Water', 'Dist_Green']:
            # Distance: use max observed (far from feature)
            fill_val = df[col].quantile(0.95)
            df[col] = df[col].fillna(fill_val)
            strategy = f'P95={fill_val:.0f}m (assume far from feature)'
        elif col in numeric_cols:
            # Default: median
            df[col] = df[col].fillna(df[col].median())
            strategy = f'median={df[col].median():.4f}'
        else:
            df[col] = df[col].fillna('Unknown')
            strategy = 'Unknown'
        
        log_step(9, f'  Impute {col}', f'{n_missing} NaN -> {strategy}')
    
    # Final check
    remaining = df.isna().sum().sum()
    log_step(9, 'Missing values resolved', f'{total_missing} NaN -> {remaining} remaining')
    
    return df


# ============================================================================
# STEP 10: ENCODE CATEGORICAL VARIABLES
# ============================================================================

def step10_encode_categoricals(df):
    """One-hot encode LULC categorical columns."""
    print('\n' + '=' * 70)
    print('  STEP 10: ENCODE CATEGORICAL VARIABLES')
    print('=' * 70)
    
    encoded_cols = []
    
    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            continue
        
        # Map codes to readable labels
        if col == 'LULC_ESA':
            labels = ESA_CLASSES
        elif col == 'LULC_DW':
            labels = DW_CLASSES
        else:
            labels = None
        
        # Get unique values
        unique_vals = sorted(df[col].dropna().unique())
        
        # Create one-hot columns with readable names
        for val in unique_vals:
            val_int = int(val)
            if labels and val_int in labels:
                new_col = f'{col}_{labels[val_int]}'
            else:
                new_col = f'{col}_{val_int}'
            
            df[new_col] = (df[col] == val).astype(int)
            encoded_cols.append(new_col)
        
        log_step(10, f'Encode {col}', 
                 f'{len(unique_vals)} classes -> {len(unique_vals)} binary columns')
    
    # Keep original columns for reference but mark them
    log_step(10, 'Encoding complete', 
             f'{len(encoded_cols)} one-hot columns created from {len(CATEGORICAL_COLS)} categoricals')
    
    return df, encoded_cols


# ============================================================================
# STEP 11: NORMALIZE NUMERICAL FEATURES
# ============================================================================

def step11_normalize(df):
    """Normalize numerical features using StandardScaler and MinMaxScaler."""
    print('\n' + '=' * 70)
    print('  STEP 11: NORMALIZE NUMERICAL FEATURES')
    print('=' * 70)
    
    scalers = {}
    
    # 11a. StandardScaler for features with wide/normal distributions
    std_cols = [c for c in STANDARD_SCALE_FEATURES if c in df.columns]
    if std_cols:
        scaler = StandardScaler()
        df[[f'{c}_zscore' for c in std_cols]] = scaler.fit_transform(df[std_cols])
        scalers['StandardScaler'] = {
            'features': std_cols,
            'means': dict(zip(std_cols, scaler.mean_.tolist())),
            'stds': dict(zip(std_cols, scaler.scale_.tolist())),
        }
        log_step(11, 'StandardScaler', 
                 f'{len(std_cols)} features -> z-score normalized (mean=0, std=1)')
    
    # 11b. MinMaxScaler for bounded features
    mm_cols = [c for c in MINMAX_SCALE_FEATURES if c in df.columns]
    if mm_cols:
        scaler = MinMaxScaler()
        df[[f'{c}_norm' for c in mm_cols]] = scaler.fit_transform(df[mm_cols])
        scalers['MinMaxScaler'] = {
            'features': mm_cols,
            'mins': dict(zip(mm_cols, scaler.data_min_.tolist())),
            'maxs': dict(zip(mm_cols, scaler.data_max_.tolist())),
        }
        log_step(11, 'MinMaxScaler',
                 f'{len(mm_cols)} features -> [0,1] normalized')
    
    # 11c. Circular encoding for angular features (Aspect, WindDirection)
    for col in ['Aspect', 'WindDirection']:
        if col in df.columns:
            rad = np.deg2rad(df[col])
            df[f'{col}_sin'] = np.sin(rad).round(6)
            df[f'{col}_cos'] = np.cos(rad).round(6)
    
    log_step(11, 'Circular encoding', 'Aspect + WindDirection -> sin/cos components')
    
    return df, scalers


# ============================================================================
# STEP 12: BUILD FINAL DATASET
# ============================================================================

def step12_build_final(df, encoded_cols, scalers):
    """Assemble the final AI-ready dataset with proper column ordering."""
    print('\n' + '=' * 70)
    print('  STEP 12: BUILD FINAL AI-READY DATASET')
    print('=' * 70)
    
    # Define column order for the master dataset
    # Keep both raw and normalized versions
    final_columns = []
    
    # 1. Metadata
    for c in META_COLS:
        if c in df.columns:
            final_columns.append(c)
    
    # 2. Target
    final_columns.append(TARGET)
    
    # 3. Raw features (original values)
    raw_features = [
        'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo', 'Impervious_Frac',
        'LULC_ESA', 'LULC_DW',
        'Population_Density',
        'Building_Height', 'Building_Density', 'Building_Volume',
        'Road_Density_Proxy', 'Street_Width_Proxy',
        'Tree_Cover_Pct',
        'Dist_Water', 'Dist_Green',
        'Elevation', 'Slope', 'Aspect',
        'AirTemp', 'Humidity', 'WindSpeed', 'WindDirection',
        'SolarRadiation', 'Cloud_Cover_Proxy', 'Pressure', 'Rainfall',
        'Nighttime_Lights',
        'UHI_Intensity', 'UTFVI', 'UTCI_Approx',
        'Anthropogenic_Heat', 'Green_Space_Density', 'Surface_Roughness',
        'QualityScore',
    ]
    for c in raw_features:
        if c in df.columns:
            final_columns.append(c)
    
    # 4. One-hot encoded columns
    for c in encoded_cols:
        if c in df.columns:
            final_columns.append(c)
    
    # 5. Normalized columns
    norm_cols = [c for c in df.columns if c.endswith('_zscore') or c.endswith('_norm')
                 or c.endswith('_sin') or c.endswith('_cos')]
    final_columns.extend(sorted(norm_cols))
    
    # Remove duplicates while preserving order
    seen = set()
    ordered = []
    for c in final_columns:
        if c not in seen and c in df.columns:
            ordered.append(c)
            seen.add(c)
    
    df_final = df[ordered].copy()
    
    log_step(12, 'Final dataset',
             f'{len(df_final)} rows x {len(df_final.columns)} columns')
    
    return df_final


# ============================================================================
# STEP 13: GENERATE OUTPUTS
# ============================================================================

def step13_generate_outputs(df_final, scalers, output_dir, city_name):
    """Generate master_dataset.csv, metadata.json, and feature_dictionary.md."""
    print('\n' + '=' * 70)
    print('  STEP 13: GENERATE OUTPUT FILES')
    print('=' * 70)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # ─── 13a. master_dataset.csv ─────────────────────────────────────────────
    csv_path = os.path.join(output_dir, 'master_dataset.csv')
    df_final.to_csv(csv_path, index=False, float_format='%.6f')
    csv_size = os.path.getsize(csv_path) / 1024
    log_step(13, 'master_dataset.csv', f'Saved ({csv_size:.1f} KB)')
    
    # ─── 13b. Train / Val / Test splits ──────────────────────────────────────
    # Exclude metadata columns from feature set
    feature_cols = [c for c in df_final.columns if c not in META_COLS]
    
    # Split: 70% train, 15% val, 15% test
    train_df, temp_df = train_test_split(df_final, test_size=0.3, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    
    train_path = os.path.join(output_dir, f'{city_name}_train.csv')
    val_path = os.path.join(output_dir, f'{city_name}_val.csv')
    test_path = os.path.join(output_dir, f'{city_name}_test.csv')
    
    train_df.to_csv(train_path, index=False, float_format='%.6f')
    val_df.to_csv(val_path, index=False, float_format='%.6f')
    test_df.to_csv(test_path, index=False, float_format='%.6f')
    
    log_step(13, 'Data splits', 
             f'Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}')
    
    # ─── 13c. metadata.json ──────────────────────────────────────────────────
    # Compute statistics for all numeric columns
    numeric_cols = df_final.select_dtypes(include=[np.number]).columns
    feature_stats = {}
    for col in numeric_cols:
        feature_stats[col] = {
            'mean': round(float(df_final[col].mean()), 6),
            'std': round(float(df_final[col].std()), 6),
            'min': round(float(df_final[col].min()), 6),
            'max': round(float(df_final[col].max()), 6),
            'median': round(float(df_final[col].median()), 6),
            'missing_pct': round(float(df_final[col].isna().mean() * 100), 2),
            'unique': int(df_final[col].nunique()),
        }
    
    metadata = {
        'project': 'Urban Heat AI - ISRO Bharatiya Antariksh Hackathon',
        'version': '2.1',
        'generated_at': datetime.now().isoformat(),
        'city': city_name,
        'dataset': {
            'total_rows': len(df_final),
            'total_columns': len(df_final.columns),
            'column_names': list(df_final.columns),
            'target_variable': TARGET,
            'metadata_columns': [c for c in META_COLS if c in df_final.columns],
            'raw_feature_count': len([c for c in df_final.columns 
                                      if c not in META_COLS 
                                      and not c.endswith(('_zscore','_norm','_sin','_cos'))
                                      and not c.startswith(('LULC_ESA_','LULC_DW_'))]),
            'encoded_feature_count': len([c for c in df_final.columns 
                                          if c.startswith(('LULC_ESA_','LULC_DW_'))]),
            'normalized_feature_count': len([c for c in df_final.columns 
                                             if c.endswith(('_zscore','_norm','_sin','_cos'))]),
        },
        'splits': {
            'train': {'rows': len(train_df), 'file': os.path.basename(train_path)},
            'validation': {'rows': len(val_df), 'file': os.path.basename(val_path)},
            'test': {'rows': len(test_df), 'file': os.path.basename(test_path)},
            'split_ratio': '70/15/15',
            'random_seed': 42,
        },
        'crs': 'EPSG:4326',
        'spatial_resolution_m': 30,
        'temporal_coverage': 'Composite (median over date range)',
        'normalization': scalers,
        'feature_statistics': feature_stats,
        'preprocessing_log': PROCESSING_LOG,
    }
    
    meta_path = os.path.join(output_dir, 'metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    log_step(13, 'metadata.json', f'Saved ({os.path.getsize(meta_path)/1024:.1f} KB)')
    
    # ─── 13d. feature_dictionary.md ──────────────────────────────────────────
    fd_path = os.path.join(output_dir, 'feature_dictionary.md')
    with open(fd_path, 'w') as f:
        f.write('# Feature Dictionary - Master Dataset\n\n')
        f.write(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write(f'Total columns: {len(df_final.columns)}\n\n')
        f.write('---\n\n')
        
        # Metadata
        f.write('## Metadata Columns\n\n')
        f.write('| Column | Type | Description |\n')
        f.write('|--------|------|-------------|\n')
        f.write('| PixelID | int | Sequential pixel identifier |\n')
        f.write('| Latitude | float | WGS84 latitude (degrees) |\n')
        f.write('| Longitude | float | WGS84 longitude (degrees) |\n')
        f.write('| Timestamp | string | Composite date range |\n\n')
        
        # Target
        f.write('## Target Variable\n\n')
        f.write('| Column | Units | Range | Description |\n')
        f.write('|--------|-------|-------|-------------|\n')
        f.write(f'| LST | Celsius | {feature_stats.get("LST",{}).get("min","?")} - '
                f'{feature_stats.get("LST",{}).get("max","?")} | '
                f'Land Surface Temperature |\n\n')
        
        # Raw features by category
        categories = {
            'Spectral Indices': ['NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo'],
            'Land Cover': ['LULC_ESA', 'LULC_DW', 'Impervious_Frac', 'Tree_Cover_Pct'],
            'Weather': ['AirTemp', 'Humidity', 'WindSpeed', 'WindDirection', 
                        'SolarRadiation', 'Cloud_Cover_Proxy', 'Pressure', 'Rainfall'],
            'Terrain': ['Elevation', 'Slope', 'Aspect'],
            'Urban Morphology': ['Building_Density', 'Building_Height', 'Building_Volume',
                                 'Road_Density_Proxy', 'Street_Width_Proxy',
                                 'Nighttime_Lights', 'Population_Density'],
            'Distance Features': ['Dist_Water', 'Dist_Green'],
            'Heat Indices': ['UHI_Intensity', 'UTFVI', 'UTCI_Approx'],
            'Derived / Proxy': ['Anthropogenic_Heat', 'Green_Space_Density',
                                'Surface_Roughness'],
            'Quality': ['QualityScore'],
        }
        
        units_map = {
            'NDVI': 'dimensionless', 'NDBI': 'dimensionless', 'NDWI': 'dimensionless',
            'MNDWI': 'dimensionless', 'SAVI': 'dimensionless', 'Albedo': 'fraction',
            'LULC_ESA': 'class code', 'LULC_DW': 'class code',
            'Impervious_Frac': 'binary', 'Tree_Cover_Pct': '%',
            'AirTemp': 'Celsius', 'Humidity': '%', 'WindSpeed': 'm/s',
            'WindDirection': 'degrees', 'SolarRadiation': 'W/m2',
            'Cloud_Cover_Proxy': 'fraction', 'Pressure': 'hPa', 'Rainfall': 'mm',
            'Elevation': 'meters', 'Slope': 'degrees', 'Aspect': 'degrees',
            'Building_Density': 'fraction', 'Building_Height': 'meters',
            'Building_Volume': 'm3/pixel', 'Road_Density_Proxy': 'unitless',
            'Street_Width_Proxy': 'meters', 'Nighttime_Lights': 'nW/cm2/sr',
            'Population_Density': 'people/pixel', 'Dist_Water': 'meters',
            'Dist_Green': 'meters', 'UHI_Intensity': 'Celsius',
            'UTFVI': 'dimensionless', 'UTCI_Approx': 'Celsius',
            'Anthropogenic_Heat': 'unitless', 'Green_Space_Density': 'fraction',
            'Surface_Roughness': 'meters', 'QualityScore': 'count',
        }
        
        desc_map = {
            'NDVI': 'Vegetation health (NIR-Red)/(NIR+Red)',
            'NDBI': 'Built-up surfaces (SWIR-NIR)/(SWIR+NIR)',
            'NDWI': 'Water bodies (Green-NIR)/(Green+NIR)',
            'MNDWI': 'Modified water index (Green-SWIR)/(Green+SWIR)',
            'SAVI': 'Soil-adjusted vegetation (Huete 1988, L=0.5)',
            'Albedo': 'Surface reflectivity (Liang 2001)',
            'LULC_ESA': 'ESA WorldCover class (10m)',
            'LULC_DW': 'Dynamic World class (10m)',
            'Impervious_Frac': 'Impervious surface flag (GAIA)',
            'Tree_Cover_Pct': 'Tree canopy cover % (Hansen)',
            'AirTemp': '2m air temperature (ERA5-Land)',
            'Humidity': 'Relative humidity (Magnus formula)',
            'WindSpeed': '10m wind speed (ERA5-Land)',
            'WindDirection': 'Wind direction meteorological (ERA5)',
            'SolarRadiation': 'Downward shortwave radiation (ERA5)',
            'Cloud_Cover_Proxy': 'Cloud cover estimate (1-SR/350)',
            'Pressure': 'Surface pressure (ERA5-Land)',
            'Rainfall': 'Accumulated precipitation (ERA5)',
            'Elevation': 'Terrain height ASL (SRTM 30m)',
            'Slope': 'Terrain slope angle (SRTM)',
            'Aspect': 'Terrain aspect direction (SRTM)',
            'Building_Density': 'Built-up surface fraction (GHSL)',
            'Building_Height': 'Average building height (GHSL)',
            'Building_Volume': 'Building volume proxy (density x height)',
            'Road_Density_Proxy': 'Road density (impervious - built-up)',
            'Street_Width_Proxy': 'Estimated street width (5-30m)',
            'Nighttime_Lights': 'VIIRS nighttime radiance',
            'Population_Density': 'Gridded population (WorldPop 100m)',
            'Dist_Water': 'Distance to nearest water body',
            'Dist_Green': 'Distance to nearest green space',
            'UHI_Intensity': 'LST minus rural mean LST',
            'UTFVI': 'Urban Thermal Field Variance Index',
            'UTCI_Approx': 'Approximate Universal Thermal Climate Index',
            'Anthropogenic_Heat': 'Waste heat proxy (NTL x Pop)',
            'Green_Space_Density': 'Green fraction in 150m neighborhood',
            'Surface_Roughness': 'Elevation StdDev in 150m neighborhood',
            'QualityScore': 'Valid Landsat observations count',
        }
        
        for cat_name, cols in categories.items():
            avail = [c for c in cols if c in df_final.columns]
            if not avail:
                continue
            f.write(f'## {cat_name}\n\n')
            f.write('| Column | Units | Min | Max | Mean | Description |\n')
            f.write('|--------|-------|-----|-----|------|-------------|\n')
            for col in avail:
                stats = feature_stats.get(col, {})
                unit = units_map.get(col, '?')
                desc = desc_map.get(col, '')
                f.write(f'| {col} | {unit} | '
                        f'{stats.get("min", "?")} | {stats.get("max", "?")} | '
                        f'{stats.get("mean", "?")} | {desc} |\n')
            f.write('\n')
        
        # One-hot encoded columns
        ohe_cols = [c for c in df_final.columns if c.startswith(('LULC_ESA_', 'LULC_DW_'))]
        if ohe_cols:
            f.write('## One-Hot Encoded LULC\n\n')
            f.write('| Column | Type | Description |\n')
            f.write('|--------|------|-------------|\n')
            for col in sorted(ohe_cols):
                f.write(f'| {col} | binary (0/1) | Land cover class indicator |\n')
            f.write('\n')
        
        # Normalized columns
        norm_cols = [c for c in df_final.columns 
                     if c.endswith(('_zscore', '_norm', '_sin', '_cos'))]
        if norm_cols:
            f.write('## Normalized Features\n\n')
            f.write('| Column | Method | Description |\n')
            f.write('|--------|--------|-------------|\n')
            for col in sorted(norm_cols):
                if col.endswith('_zscore'):
                    method = 'StandardScaler (mean=0, std=1)'
                elif col.endswith('_norm'):
                    method = 'MinMaxScaler [0, 1]'
                elif col.endswith('_sin'):
                    method = 'Circular sin encoding'
                elif col.endswith('_cos'):
                    method = 'Circular cos encoding'
                else:
                    method = '?'
                base = col.rsplit('_', 1)[0] if '_' in col else col
                f.write(f'| {col} | {method} | Normalized {base} |\n')
            f.write('\n')
        
        # Preprocessing log
        f.write('## Preprocessing Steps\n\n')
        f.write('| Step | Name | Detail |\n')
        f.write('|------|------|--------|\n')
        for entry in PROCESSING_LOG:
            f.write(f'| {entry["step"]:02d} | {entry["name"]} | {entry["detail"]} |\n')
        f.write('\n')
    
    log_step(13, 'feature_dictionary.md', f'Saved ({os.path.getsize(fd_path)/1024:.1f} KB)')
    
    return csv_path, meta_path, fd_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Prepare AI-ready master dataset from GEE-exported CSV.'
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Path to GEE-exported CSV file')
    parser.add_argument('--output-dir', '-o', default=None,
                        help='Output directory (default: same as input)')
    parser.add_argument('--city', '-c', default=None,
                        help='City name (default: extracted from filename)')
    args = parser.parse_args()
    
    output_dir = args.output_dir or os.path.dirname(args.input) or '.'
    city_name = args.city or os.path.basename(args.input).split('_')[0]
    
    print('\n' + '#' * 70)
    print('#' + ' ' * 68 + '#')
    print('#    URBAN HEAT AI - ML DATASET PREPARATION PIPELINE' + ' ' * 17 + '#')
    print('#    ISRO Bharatiya Antariksh Hackathon' + ' ' * 30 + '#')
    print('#' + ' ' * 68 + '#')
    print('#' * 70)
    print(f'\n  City:   {city_name}')
    print(f'  Input:  {args.input}')
    print(f'  Output: {output_dir}')
    
    # Execute pipeline
    df = step01_load(args.input)
    df = step02_validate_schema(df)
    df = step03_normalize_crs(df)
    df = step04_align_timestamps(df)
    df = step05_remove_invalid(df)
    df = step06_remove_cloudy(df)
    df = step07_remove_duplicates(df)
    df = step08_compute_derived(df)
    df = step09_handle_missing(df)
    df, encoded_cols = step10_encode_categoricals(df)
    df, scalers = step11_normalize(df)
    df_final = step12_build_final(df, encoded_cols, scalers)
    csv_path, meta_path, fd_path = step13_generate_outputs(
        df_final, scalers, output_dir, city_name)
    
    # Summary
    print('\n' + '#' * 70)
    print('#    PIPELINE COMPLETE' + ' ' * 47 + '#')
    print('#' * 70)
    print(f'\n  master_dataset.csv:     {csv_path}')
    print(f'  metadata.json:          {meta_path}')
    print(f'  feature_dictionary.md:  {fd_path}')
    print(f'\n  Dataset: {len(df_final):,} rows x {len(df_final.columns)} columns')
    print(f'  Target:  {TARGET}')
    
    raw_count = len([c for c in df_final.columns 
                     if c not in META_COLS 
                     and not c.endswith(('_zscore','_norm','_sin','_cos'))
                     and not c.startswith(('LULC_ESA_','LULC_DW_'))])
    ohe_count = len([c for c in df_final.columns 
                     if c.startswith(('LULC_ESA_','LULC_DW_'))])
    norm_count = len([c for c in df_final.columns 
                      if c.endswith(('_zscore','_norm','_sin','_cos'))])
    
    print(f'\n  Raw features:         {raw_count}')
    print(f'  One-hot encoded:      {ohe_count}')
    print(f'  Normalized:           {norm_count}')
    print(f'  Total columns:        {len(df_final.columns)}')
    
    print(f'\n  Quick start:')
    print(f'    import pandas as pd')
    print(f'    df = pd.read_csv("{csv_path}")')
    print(f'    X = df.drop(columns={META_COLS + [TARGET]})')
    print(f'    y = df["{TARGET}"]')
    print()


if __name__ == '__main__':
    main()
