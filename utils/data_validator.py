"""
Urban Heat AI — Data Validator & Preprocessor
==============================================
Post-download Python utility for validating and preparing the GEE-exported
master CSV dataset for machine learning.

Usage:
    python data_validator.py --input path/to/Delhi_UHI_MasterDataset.csv

Requirements:
    pip install pandas numpy scikit-learn

This script:
    1. Loads the CSV exported from Google Earth Engine
    2. Validates data types, ranges, and completeness
    3. Removes invalid/outlier rows
    4. One-hot encodes categorical LULC columns
    5. Creates train/test/validation splits
    6. Saves ML-ready datasets
    7. Generates a quality report
"""

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd


# ─── Feature Definitions ────────────────────────────────────────────────────
# Expected columns with their data types and valid ranges.
FEATURE_SCHEMA = {
    # Metadata
    'PixelID':           {'type': 'int',   'min': 0,      'max': None},
    'Latitude':          {'type': 'float', 'min': 6.0,    'max': 38.0},    # India bounds
    'Longitude':         {'type': 'float', 'min': 68.0,   'max': 98.0},    # India bounds
    # Target
    'LST':               {'type': 'float', 'min': -10.0,  'max': 70.0},
    # Spectral Indices
    'NDVI':              {'type': 'float', 'min': -1.0,   'max': 1.0},
    'NDBI':              {'type': 'float', 'min': -1.0,   'max': 1.0},
    'NDWI':              {'type': 'float', 'min': -1.0,   'max': 1.0},
    'MNDWI':             {'type': 'float', 'min': -1.0,   'max': 1.0},
    'Albedo':            {'type': 'float', 'min': 0.0,    'max': 1.0},
    # Land Cover
    'LULC_ESA':          {'type': 'int',   'min': 10,     'max': 100},
    'LULC_DW':           {'type': 'int',   'min': 0,      'max': 8},
    'Impervious_Frac':   {'type': 'int',   'min': 0,      'max': 1},
    'Tree_Cover_Pct':    {'type': 'float', 'min': 0.0,    'max': 100.0},
    # Weather
    'AirTemp':           {'type': 'float', 'min': -10.0,  'max': 60.0},
    'Humidity':          {'type': 'float', 'min': 0.0,    'max': 100.0},
    'WindSpeed':         {'type': 'float', 'min': 0.0,    'max': 30.0},
    'WindDirection':     {'type': 'float', 'min': 0.0,    'max': 360.0},
    'SolarRadiation':    {'type': 'float', 'min': 0.0,    'max': 500.0},
    'Pressure':          {'type': 'float', 'min': 800.0,  'max': 1100.0},
    'Rainfall':          {'type': 'float', 'min': 0.0,    'max': 5000.0},
    # Terrain
    'Elevation':         {'type': 'float', 'min': -100.0, 'max': 9000.0},
    'Slope':             {'type': 'float', 'min': 0.0,    'max': 90.0},
    'Aspect':            {'type': 'float', 'min': 0.0,    'max': 360.0},
    # Urban Morphology
    'Building_Density':  {'type': 'float', 'min': 0.0,    'max': None},
    'Building_Height':   {'type': 'float', 'min': 0.0,    'max': 500.0},
    'Building_Volume':   {'type': 'float', 'min': 0.0,    'max': None},
    'Nighttime_Lights':  {'type': 'float', 'min': 0.0,    'max': 500.0},
    'Population_Density':{'type': 'float', 'min': 0.0,    'max': None},
    # Distance
    'Dist_Water':        {'type': 'float', 'min': 0.0,    'max': None},
    'Dist_Green':        {'type': 'float', 'min': 0.0,    'max': None},
    # Derived
    'Green_Space_Density':{'type': 'float','min': 0.0,    'max': 1.0},
    'Surface_Roughness': {'type': 'float', 'min': 0.0,    'max': None},
    'Anthropogenic_Heat':{'type': 'float', 'min': 0.0,    'max': None},
    'Road_Density_Proxy':{'type': 'float', 'min': -1.0,   'max': 1.0},
    # Heat Indices
    'UHI_Intensity':     {'type': 'float', 'min': -20.0,  'max': 25.0},
    'UTFVI':             {'type': 'float', 'min': -1.0,   'max': 1.0},
    # Quality
    'QualityScore':      {'type': 'int',   'min': 0,      'max': None},
}

# Columns to exclude from ML features.
METADATA_COLS = ['PixelID', 'Latitude', 'Longitude', 'Timestamp']
TARGET_COL = 'LST'
CATEGORICAL_COLS = ['LULC_ESA', 'LULC_DW']


def load_data(filepath: str) -> pd.DataFrame:
    """Load the CSV exported from Google Earth Engine."""
    print(f"\n[LOAD] Loading: {filepath}")
    df = pd.read_csv(filepath)
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns)}")
    return df


def validate_columns(df: pd.DataFrame) -> dict:
    """Check which expected columns are present."""
    expected = set(FEATURE_SCHEMA.keys())
    actual = set(df.columns)
    missing = expected - actual
    extra = actual - expected - {'Timestamp', 'system:index', '.geo'}

    report = {
        'expected_columns': len(expected),
        'found_columns': len(actual),
        'missing_columns': list(missing),
        'extra_columns': list(extra),
    }

    if missing:
        print(f"   [WARN] Missing columns: {missing}")
    else:
        print(f"   [OK] All {len(expected)} expected columns found.")

    return report


def validate_ranges(df: pd.DataFrame) -> dict:
    """Check that values fall within expected ranges."""
    issues = {}
    for col, schema in FEATURE_SCHEMA.items():
        if col not in df.columns:
            continue

        col_data = df[col].dropna()
        if len(col_data) == 0:
            issues[col] = 'ALL_NULL'
            continue

        violations = 0
        if schema['min'] is not None:
            violations += (col_data < schema['min']).sum()
        if schema['max'] is not None:
            violations += (col_data > schema['max']).sum()

        if violations > 0:
            issues[col] = f'{violations} values out of range'

    if issues:
        print(f"   [WARN] Range issues in {len(issues)} columns:")
        for col, issue in issues.items():
            print(f"      {col}: {issue}")
    else:
        print("   [OK] All values within expected ranges.")

    return issues


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove invalid rows and handle edge cases."""
    original_len = len(df)

    # Drop rows with NaN in critical columns.
    critical = [TARGET_COL, 'NDVI', 'NDBI', 'NDWI', 'Elevation']
    available_critical = [c for c in critical if c in df.columns]
    df = df.dropna(subset=available_critical)

    # Clamp values to valid ranges.
    for col, schema in FEATURE_SCHEMA.items():
        if col not in df.columns:
            continue
        if schema['min'] is not None:
            df[col] = df[col].clip(lower=schema['min'])
        if schema['max'] is not None:
            df[col] = df[col].clip(upper=schema['max'])

    # Remove rows where LST is unreasonable (likely sensor error).
    if TARGET_COL in df.columns:
        df = df[(df[TARGET_COL] > 0) & (df[TARGET_COL] < 65)]

    # Fill remaining NaN with column median (for non-critical columns).
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    removed = original_len - len(df)
    print(f"   [OK] Cleaned: {removed:,} rows removed ({removed/original_len*100:.1f}%)")
    print(f"   [OK] Final size: {len(df):,} rows")
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode categorical LULC columns."""
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            dummies = pd.get_dummies(df[col], prefix=col, dtype=int)
            df = pd.concat([df, dummies], axis=1)
            # Keep original for reference but exclude from ML features later.
    print(f"   [OK] One-hot encoded: {CATEGORICAL_COLS}")
    return df


def split_data(df: pd.DataFrame, test_size=0.2, val_size=0.1, seed=42):
    """Split into train/validation/test sets."""
    from sklearn.model_selection import train_test_split

    # Determine feature columns (exclude metadata, target, original categoricals).
    exclude = set(METADATA_COLS + [TARGET_COL])
    feature_cols = [c for c in df.columns if c not in exclude]

    X = df[feature_cols]
    y = df[TARGET_COL]

    # First split: train+val vs test.
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    # Second split: train vs val.
    val_relative = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=val_relative, random_state=seed
    )

    print(f"   [OK] Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
    return X_train, X_val, X_test, y_train, y_val, y_test, feature_cols


def generate_report(df: pd.DataFrame, col_report: dict, range_issues: dict,
                    feature_cols: list, output_dir: str):
    """Generate a JSON quality report."""
    report = {
        'generated_at': datetime.now().isoformat(),
        'dataset_shape': {'rows': len(df), 'columns': len(df.columns)},
        'column_validation': col_report,
        'range_issues': range_issues,
        'feature_count': len(feature_cols),
        'target_variable': TARGET_COL,
        'target_statistics': {
            'mean': float(df[TARGET_COL].mean()),
            'std': float(df[TARGET_COL].std()),
            'min': float(df[TARGET_COL].min()),
            'max': float(df[TARGET_COL].max()),
            'median': float(df[TARGET_COL].median()),
        },
        'missing_values_per_column': {
            col: int(df[col].isna().sum())
            for col in df.columns if df[col].isna().sum() > 0
        },
        'feature_statistics': {
            col: {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
            }
            for col in feature_cols if col in df.columns and
            pd.api.types.is_numeric_dtype(df[col])
        },
    }

    report_path = os.path.join(output_dir, 'quality_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"   [OK] Quality report saved: {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Validate and prepare UHI master dataset for ML training.'
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Path to the master CSV file from GEE')
    parser.add_argument('--output-dir', '-o', default=None,
                        help='Output directory (default: same as input)')
    parser.add_argument('--test-size', type=float, default=0.2,
                        help='Test set fraction (default: 0.2)')
    parser.add_argument('--val-size', type=float, default=0.1,
                        help='Validation set fraction (default: 0.1)')
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.dirname(args.input) or '.'
    os.makedirs(output_dir, exist_ok=True)

    city = os.path.basename(args.input).split('_')[0]

    print("=" * 60)
    print("  URBAN HEAT AI - DATA VALIDATION & PREPARATION")
    print("=" * 60)

    # 1. Load
    df = load_data(args.input)

    # 2. Validate columns
    print("\n[STEP] Validating columns...")
    col_report = validate_columns(df)

    # 3. Validate ranges
    print("\n[STEP] Validating value ranges...")
    range_issues = validate_ranges(df)

    # 4. Clean
    print("\n[STEP] Cleaning data...")
    df = clean_data(df)

    # 5. Encode categoricals
    print("\n[STEP] Encoding categorical features...")
    df = encode_categoricals(df)

    # 6. Split
    print("\n[STEP] Splitting into train/val/test...")
    X_train, X_val, X_test, y_train, y_val, y_test, feature_cols = split_data(
        df, test_size=args.test_size, val_size=args.val_size
    )

    # 7. Save
    print("\n[STEP] Saving processed datasets...")
    train_df = pd.concat([X_train, y_train], axis=1)
    val_df = pd.concat([X_val, y_val], axis=1)
    test_df = pd.concat([X_test, y_test], axis=1)

    train_path = os.path.join(output_dir, f'{city}_train.csv')
    val_path = os.path.join(output_dir, f'{city}_val.csv')
    test_path = os.path.join(output_dir, f'{city}_test.csv')

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    print(f"   [OK] {train_path}")
    print(f"   [OK] {val_path}")
    print(f"   [OK] {test_path}")

    # 8. Report
    print("\n[STEP] Generating quality report...")
    generate_report(df, col_report, range_issues, feature_cols, output_dir)

    print("\n" + "=" * 60)
    print("  VALIDATION COMPLETE")
    print("=" * 60)
    print(f"\n  ML-ready files saved to: {output_dir}")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Target: {TARGET_COL}")
    print(f"\n  Quick start in Python:")
    print(f"    import pandas as pd")
    print(f"    train = pd.read_csv('{train_path}')")
    print(f"    X = train.drop(columns=['{TARGET_COL}'])")
    print(f"    y = train['{TARGET_COL}']")
    print()


if __name__ == '__main__':
    main()
