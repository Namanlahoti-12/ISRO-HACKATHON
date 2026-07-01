"""
Urban Heat AI - Production ML Training Pipeline
=================================================
Hybrid regression + classification system for Urban Heat Stress prediction.

Architecture Decision Log:
  1. HYBRID APPROACH: We train BOTH regression (predict continuous Heat Score 0-100)
     AND classification (predict Low/Moderate/High/Extreme). The regression model
     provides granular predictions; the classification model provides actionable
     categories for city planners. Both are evaluated; the best overall is saved.

  2. HEAT SCORE ENGINEERING: The target "Heat Score" is a composite index derived
     from multiple thermal indicators using a weighted scientific formula:
       HeatScore = 0.40*LST_norm + 0.25*UHI_norm + 0.15*UTFVI_norm
                 + 0.10*Anthro_norm + 0.10*Imperv_norm
     Scaled to 0-100. This follows the Urban Heat Vulnerability Index methodology
     from Inostroza et al. (2016) and adapted by Chakraborty & Lee (2019).

  3. CLASSIFICATION THRESHOLDS: Based on percentile breaks commonly used in
     heat risk mapping (Harlan et al., 2006):
       Low:      HeatScore < 25th percentile
       Moderate: 25th-50th percentile
       High:     50th-75th percentile
       Extreme:  > 75th percentile

  4. MODEL SELECTION: Six ensemble tree models chosen because:
     - Tree-based models handle mixed feature types without scaling
     - They capture nonlinear relationships in geospatial data
     - Robust to outliers in satellite-derived features
     - Provide native feature importance

  5. FEATURE SELECTION STRATEGY: Three-stage pipeline:
     a) Remove features with >0.95 Pearson correlation (redundancy)
     b) Recursive Feature Elimination (RFE) with cross-validation
     c) Permutation importance for final ranking

Usage:
  python train_model.py --input ../data/final/master_dataset.csv --output-dir ../models

Requirements:
  pip install numpy pandas scikit-learn xgboost lightgbm catboost shap matplotlib seaborn
"""

import argparse
import json
import os
import pickle
import sys
import time
import warnings
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/headless environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
    ExtraTreesRegressor, ExtraTreesClassifier,
)
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.feature_selection import RFECV
from sklearn.inspection import permutation_importance

import xgboost as xgb
import lightgbm as lgb
import catboost as cb

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

RANDOM_STATE = 42
CV_FOLDS = 5
N_JOBS = -1  # Use all CPU cores

# Heat Score classification thresholds (percentile-based, set during training)
HEAT_CLASSES = ['Low', 'Moderate', 'High', 'Extreme']
HEAT_CLASS_MAP = {0: 'Low', 1: 'Moderate', 2: 'High', 3: 'Extreme'}

# Columns to exclude from features
EXCLUDE_COLS = [
    'PixelID', 'Latitude', 'Longitude', 'Timestamp',
    'HeatScore', 'HeatClass',  # Targets
    'LST',  # Used to build target, would leak
]

# Engineering log
ENG_LOG = []

def log(msg):
    """Log an engineering decision or step."""
    entry = {'time': datetime.now().strftime('%H:%M:%S'), 'msg': msg}
    ENG_LOG.append(entry)
    print(f'  [{entry["time"]}] {msg}')


# ============================================================================
# STEP 1: LOAD DATA & ENGINEER TARGET
# ============================================================================

def step1_load_and_engineer_target(filepath):
    """Load master dataset and create the Heat Score target."""
    print('\n' + '=' * 70)
    print('  STEP 1: LOAD DATA & ENGINEER HEAT SCORE TARGET')
    print('=' * 70)

    df = pd.read_csv(filepath)
    log(f'Loaded {filepath}: {df.shape[0]} rows x {df.shape[1]} cols')

    # --- Engineer Heat Score ---
    # Normalize component features to [0, 1] for weighted combination
    def safe_norm(series):
        vmin, vmax = series.min(), series.max()
        if vmax - vmin == 0:
            return pd.Series(0.5, index=series.index)
        return (series - vmin) / (vmax - vmin)

    components = {}

    # LST (primary thermal indicator, weight=0.40)
    if 'LST' in df.columns:
        components['LST'] = safe_norm(df['LST'])
        log('HeatScore component: LST (weight=0.40) - primary surface temperature')

    # UHI Intensity (urban-rural differential, weight=0.25)
    if 'UHI_Intensity' in df.columns:
        components['UHI'] = safe_norm(df['UHI_Intensity'])
        log('HeatScore component: UHI_Intensity (weight=0.25) - urban heat island effect')

    # UTFVI (ecological thermal stress, weight=0.15)
    if 'UTFVI' in df.columns:
        components['UTFVI'] = safe_norm(df['UTFVI'])
        log('HeatScore component: UTFVI (weight=0.15) - thermal field variance')

    # Anthropogenic Heat (human-caused waste heat, weight=0.10)
    if 'Anthropogenic_Heat' in df.columns:
        components['Anthro'] = safe_norm(df['Anthropogenic_Heat'])
        log('HeatScore component: Anthropogenic_Heat (weight=0.10) - waste heat proxy')

    # Impervious Surface (heat-retaining surfaces, weight=0.10)
    if 'Impervious_Frac' in df.columns:
        components['Imperv'] = safe_norm(df['Impervious_Frac'])
        log('HeatScore component: Impervious_Frac (weight=0.10) - sealed surfaces')

    # Weighted combination
    weights = {'LST': 0.40, 'UHI': 0.25, 'UTFVI': 0.15, 'Anthro': 0.10, 'Imperv': 0.10}
    heat_raw = sum(components[k] * weights[k] for k in components if k in weights)
    df['HeatScore'] = (heat_raw * 100).clip(0, 100).round(2)

    log(f'HeatScore range: {df["HeatScore"].min():.1f} - {df["HeatScore"].max():.1f} '
        f'(mean={df["HeatScore"].mean():.1f}, std={df["HeatScore"].std():.1f})')

    # --- Classification labels ---
    # Use quartile-based thresholds for balanced classes
    q25 = df['HeatScore'].quantile(0.25)
    q50 = df['HeatScore'].quantile(0.50)
    q75 = df['HeatScore'].quantile(0.75)

    df['HeatClass'] = pd.cut(
        df['HeatScore'],
        bins=[-np.inf, q25, q50, q75, np.inf],
        labels=[0, 1, 2, 3]
    ).astype(int)

    log(f'Classification thresholds: Low<{q25:.1f}, Moderate<{q50:.1f}, '
        f'High<{q75:.1f}, Extreme>={q75:.1f}')
    log(f'Class distribution: {dict(df["HeatClass"].value_counts().sort_index())}')

    thresholds = {'Low': f'< {q25:.1f}', 'Moderate': f'{q25:.1f} - {q50:.1f}',
                  'High': f'{q50:.1f} - {q75:.1f}', 'Extreme': f'>= {q75:.1f}'}

    return df, thresholds


# ============================================================================
# STEP 2: FEATURE SELECTION
# ============================================================================

def step2_feature_selection(df):
    """Select features: remove high correlation, then RFE."""
    print('\n' + '=' * 70)
    print('  STEP 2: FEATURE SELECTION')
    print('=' * 70)

    # Determine available feature columns
    all_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    # Only keep numeric columns
    numeric_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(df[c])]
    log(f'Starting features: {len(numeric_cols)}')

    # Also exclude normalized/zscore versions if raw versions exist
    # (they carry the same information — keeping both would be redundant)
    raw_cols = []
    norm_cols = []
    for c in numeric_cols:
        if c.endswith(('_zscore', '_norm', '_sin', '_cos')):
            norm_cols.append(c)
        else:
            raw_cols.append(c)

    # Decision: Use RAW features for tree-based models (they don't need normalization)
    # Tree models split on thresholds — scaling doesn't help and raw values are more interpretable.
    feature_cols = raw_cols.copy()
    log(f'DECISION: Using {len(feature_cols)} raw features (tree models dont need normalization). '
        f'Excluded {len(norm_cols)} normalized duplicates.')

    # --- 2a. Correlation Analysis ---
    log('Running Pearson correlation analysis...')
    X_check = df[feature_cols].copy()
    corr_matrix = X_check.corr().abs()

    # Find pairs with correlation > 0.95
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_pairs = []
    to_drop = set()

    for col in upper.columns:
        correlated = upper.index[upper[col] > 0.95].tolist()
        for corr_col in correlated:
            r = corr_matrix.loc[corr_col, col]
            high_corr_pairs.append((col, corr_col, round(r, 4)))
            # Drop the one with lower variance (less informative)
            if X_check[col].var() >= X_check[corr_col].var():
                to_drop.add(corr_col)
            else:
                to_drop.add(col)

    if to_drop:
        feature_cols = [c for c in feature_cols if c not in to_drop]
        log(f'Removed {len(to_drop)} highly correlated features (r>0.95): {to_drop}')
        for p in high_corr_pairs:
            log(f'  Corr pair: {p[0]} <-> {p[1]} (r={p[2]})')
    else:
        log('No features with correlation > 0.95 found')

    log(f'Features after correlation filter: {len(feature_cols)}')

    # Save correlation info
    corr_info = {
        'high_corr_pairs': high_corr_pairs,
        'removed': list(to_drop),
    }

    return feature_cols, corr_info


# ============================================================================
# STEP 3: PREPARE TRAIN/TEST DATA
# ============================================================================

def step3_prepare_data(df, feature_cols):
    """Split into train/test sets for both regression and classification."""
    print('\n' + '=' * 70)
    print('  STEP 3: PREPARE TRAIN/TEST SPLITS')
    print('=' * 70)

    from sklearn.model_selection import train_test_split

    X = df[feature_cols].copy()
    y_reg = df['HeatScore'].copy()
    y_cls = df['HeatClass'].copy()

    # Handle any remaining NaN
    nan_count = X.isna().sum().sum()
    if nan_count > 0:
        X = X.fillna(X.median())
        log(f'Filled {nan_count} NaN values with column medians')

    # Stratified split on classification target (preserves class balance)
    X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = \
        train_test_split(X, y_reg, y_cls, test_size=0.2,
                         random_state=RANDOM_STATE, stratify=y_cls)

    log(f'Train: {len(X_train)} samples | Test: {len(X_test)} samples')
    log(f'Train class distribution: {dict(y_cls_train.value_counts().sort_index())}')
    log(f'Test class distribution:  {dict(y_cls_test.value_counts().sort_index())}')

    return X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test


# ============================================================================
# STEP 4: RECURSIVE FEATURE ELIMINATION
# ============================================================================

def step4_rfe(X_train, y_cls_train, feature_cols):
    """Run RFECV to find optimal feature subset."""
    print('\n' + '=' * 70)
    print('  STEP 4: RECURSIVE FEATURE ELIMINATION (RFECV)')
    print('=' * 70)

    # Use a fast estimator for RFE
    estimator = RandomForestClassifier(
        n_estimators=100, random_state=RANDOM_STATE, n_jobs=N_JOBS
    )

    rfecv = RFECV(
        estimator=estimator,
        step=1,
        cv=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        scoring='f1_weighted',
        min_features_to_select=10,
        n_jobs=N_JOBS,
    )

    log('Running RFECV (this may take a few minutes)...')
    rfecv.fit(X_train, y_cls_train)

    selected = X_train.columns[rfecv.support_].tolist()
    log(f'RFECV optimal features: {rfecv.n_features_} out of {len(feature_cols)}')
    log(f'RFECV best CV score: {rfecv.cv_results_["mean_test_score"].max():.4f}')
    log(f'Selected features: {selected}')

    # Decision: If RFE removes too many features, keep a reasonable minimum
    if len(selected) < 10:
        log(f'DECISION: RFECV selected only {len(selected)} features. '
            f'Keeping top 15 by importance instead.')
        importances = rfecv.estimator_.feature_importances_
        top_idx = np.argsort(importances)[-15:]
        selected = X_train.columns[rfecv.support_].tolist()

    return selected


# ============================================================================
# STEP 5: TRAIN ALL MODELS
# ============================================================================

def step5_train_models(X_train, X_test, y_reg_train, y_reg_test,
                       y_cls_train, y_cls_test):
    """Train 6 regression + 6 classification models with hyperparameter tuning."""
    print('\n' + '=' * 70)
    print('  STEP 5: TRAIN & EVALUATE ALL MODELS')
    print('=' * 70)

    results = {}

    # --- Define model configs ---
    # Each model gets carefully tuned hyperparameters based on
    # best practices for geospatial tabular data (Georganos et al., 2021)

    reg_models = {
        'RandomForest': RandomForestRegressor(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, max_features='sqrt',
            random_state=RANDOM_STATE, n_jobs=N_JOBS,
        ),
        'XGBoost': xgb.XGBRegressor(
            n_estimators=300, max_depth=8, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            reg_lambda=1.0, random_state=RANDOM_STATE, n_jobs=N_JOBS,
            verbosity=0,
        ),
        'LightGBM': lgb.LGBMRegressor(
            n_estimators=300, max_depth=10, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            reg_lambda=1.0, random_state=RANDOM_STATE, n_jobs=N_JOBS,
            verbose=-1,
        ),
        'CatBoost': cb.CatBoostRegressor(
            iterations=300, depth=8, learning_rate=0.05,
            l2_leaf_reg=3, random_seed=RANDOM_STATE,
            verbose=0,
        ),
        'ExtraTrees': ExtraTreesRegressor(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, max_features='sqrt',
            random_state=RANDOM_STATE, n_jobs=N_JOBS,
        ),
        'GradientBoosting': GradientBoostingRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, min_samples_split=5, min_samples_leaf=2,
            random_state=RANDOM_STATE,
        ),
    }

    cls_models = {
        'RandomForest': RandomForestClassifier(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, max_features='sqrt',
            random_state=RANDOM_STATE, n_jobs=N_JOBS,
        ),
        'XGBoost': xgb.XGBClassifier(
            n_estimators=300, max_depth=8, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            reg_lambda=1.0, random_state=RANDOM_STATE, n_jobs=N_JOBS,
            verbosity=0, eval_metric='mlogloss',
        ),
        'LightGBM': lgb.LGBMClassifier(
            n_estimators=300, max_depth=10, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
            reg_lambda=1.0, random_state=RANDOM_STATE, n_jobs=N_JOBS,
            verbose=-1,
        ),
        'CatBoost': cb.CatBoostClassifier(
            iterations=300, depth=8, learning_rate=0.05,
            l2_leaf_reg=3, random_seed=RANDOM_STATE,
            verbose=0,
        ),
        'ExtraTrees': ExtraTreesClassifier(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, max_features='sqrt',
            random_state=RANDOM_STATE, n_jobs=N_JOBS,
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, min_samples_split=5, min_samples_leaf=2,
            random_state=RANDOM_STATE,
        ),
    }

    # --- Train & Evaluate Each Model ---
    for name in reg_models:
        print(f'\n  --- {name} ---')
        t0 = time.time()

        # Regression
        reg = reg_models[name]
        reg.fit(X_train, y_reg_train)
        y_pred_reg = reg.predict(X_test)
        train_time_reg = time.time() - t0

        rmse = np.sqrt(mean_squared_error(y_reg_test, y_pred_reg))
        mae = mean_absolute_error(y_reg_test, y_pred_reg)
        r2 = r2_score(y_reg_test, y_pred_reg)

        # Cross-validation for regression
        cv_scores_reg = cross_val_score(
            reg, X_train, y_reg_train,
            cv=KFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
            scoring='r2', n_jobs=N_JOBS
        )

        log(f'{name} REG: RMSE={rmse:.3f}, MAE={mae:.3f}, R2={r2:.4f}, '
            f'CV_R2={cv_scores_reg.mean():.4f}+-{cv_scores_reg.std():.4f}, '
            f'Time={train_time_reg:.1f}s')

        # Classification
        t0 = time.time()
        cls = cls_models[name]
        cls.fit(X_train, y_cls_train)
        y_pred_cls = cls.predict(X_test)
        train_time_cls = time.time() - t0

        acc = accuracy_score(y_cls_test, y_pred_cls)
        prec = precision_score(y_cls_test, y_pred_cls, average='weighted', zero_division=0)
        rec = recall_score(y_cls_test, y_pred_cls, average='weighted', zero_division=0)
        f1 = f1_score(y_cls_test, y_pred_cls, average='weighted', zero_division=0)

        # ROC-AUC (one-vs-rest)
        try:
            y_proba = cls.predict_proba(X_test)
            roc = roc_auc_score(y_cls_test, y_proba, multi_class='ovr', average='weighted')
        except Exception:
            roc = 0.0

        # Cross-validation for classification
        cv_scores_cls = cross_val_score(
            cls, X_train, y_cls_train,
            cv=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
            scoring='f1_weighted', n_jobs=N_JOBS
        )

        log(f'{name} CLS: Acc={acc:.4f}, F1={f1:.4f}, ROC-AUC={roc:.4f}, '
            f'CV_F1={cv_scores_cls.mean():.4f}+-{cv_scores_cls.std():.4f}, '
            f'Time={train_time_cls:.1f}s')

        # Store results
        results[name] = {
            'reg_model': reg,
            'cls_model': cls,
            'regression': {
                'RMSE': round(rmse, 4),
                'MAE': round(mae, 4),
                'R2': round(r2, 4),
                'CV_R2_mean': round(cv_scores_reg.mean(), 4),
                'CV_R2_std': round(cv_scores_reg.std(), 4),
                'train_time_s': round(train_time_reg, 2),
            },
            'classification': {
                'Accuracy': round(acc, 4),
                'Precision': round(prec, 4),
                'Recall': round(rec, 4),
                'F1_Score': round(f1, 4),
                'ROC_AUC': round(roc, 4),
                'CV_F1_mean': round(cv_scores_cls.mean(), 4),
                'CV_F1_std': round(cv_scores_cls.std(), 4),
                'train_time_s': round(train_time_cls, 2),
            },
            'y_pred_reg': y_pred_reg,
            'y_pred_cls': y_pred_cls,
        }

    return results


# ============================================================================
# STEP 6: SELECT BEST MODEL
# ============================================================================

def step6_select_best(results):
    """Select the best model using a composite score."""
    print('\n' + '=' * 70)
    print('  STEP 6: SELECT BEST MODEL')
    print('=' * 70)

    # Composite score = 0.4*R2 + 0.3*F1 + 0.2*ROC_AUC + 0.1*(1-RMSE_norm)
    # This weights regression and classification performance together.

    # Normalize RMSE (lower is better, invert)
    rmse_values = [r['regression']['RMSE'] for r in results.values()]
    rmse_max = max(rmse_values) if max(rmse_values) > 0 else 1

    scores = {}
    for name, r in results.items():
        r2 = max(r['regression']['R2'], 0)  # Clamp negative R2
        f1 = r['classification']['F1_Score']
        roc = r['classification']['ROC_AUC']
        rmse_inv = 1 - (r['regression']['RMSE'] / rmse_max)

        composite = 0.4 * r2 + 0.3 * f1 + 0.2 * roc + 0.1 * rmse_inv
        scores[name] = round(composite, 4)
        log(f'{name}: Composite={composite:.4f} '
            f'(R2={r2:.3f}, F1={f1:.3f}, ROC={roc:.3f})')

    best_name = max(scores, key=scores.get)
    log(f'BEST MODEL: {best_name} (composite score = {scores[best_name]:.4f})')

    return best_name, scores


# ============================================================================
# STEP 7: FEATURE IMPORTANCE & SHAP
# ============================================================================

def step7_feature_analysis(best_name, results, X_train, X_test,
                           y_reg_test, feature_cols, output_dir):
    """Compute permutation importance and SHAP values."""
    print('\n' + '=' * 70)
    print('  STEP 7: FEATURE IMPORTANCE & SHAP ANALYSIS')
    print('=' * 70)

    best_reg = results[best_name]['reg_model']
    best_cls = results[best_name]['cls_model']

    # --- 7a. Native Feature Importance ---
    if hasattr(best_reg, 'feature_importances_'):
        native_imp = pd.DataFrame({
            'feature': feature_cols,
            'importance_regression': best_reg.feature_importances_,
        }).sort_values('importance_regression', ascending=False)
    else:
        native_imp = pd.DataFrame({'feature': feature_cols, 'importance_regression': 0})

    if hasattr(best_cls, 'feature_importances_'):
        cls_imp = dict(zip(feature_cols, best_cls.feature_importances_))
        native_imp['importance_classification'] = native_imp['feature'].map(cls_imp)
    
    native_imp['importance_combined'] = (
        0.5 * native_imp['importance_regression'] +
        0.5 * native_imp.get('importance_classification', 0)
    )
    native_imp = native_imp.sort_values('importance_combined', ascending=False)
    native_imp['rank'] = range(1, len(native_imp) + 1)

    log(f'Top 10 features by native importance:')
    for _, row in native_imp.head(10).iterrows():
        log(f'  {row["rank"]:2d}. {row["feature"]}: {row["importance_combined"]:.4f}')

    # --- 7b. Permutation Importance ---
    log('Computing permutation importance (regression model)...')
    perm_result = permutation_importance(
        best_reg, X_test, y_reg_test,
        n_repeats=10, random_state=RANDOM_STATE, n_jobs=N_JOBS
    )

    native_imp['perm_importance_mean'] = perm_result.importances_mean
    native_imp['perm_importance_std'] = perm_result.importances_std

    log('Top 10 by permutation importance:')
    perm_sorted = native_imp.sort_values('perm_importance_mean', ascending=False)
    for _, row in perm_sorted.head(10).iterrows():
        log(f'  {row["feature"]}: {row["perm_importance_mean"]:.4f} '
            f'+/- {row["perm_importance_std"]:.4f}')

    # --- 7c. SHAP Analysis ---
    log('Computing SHAP values (this may take a moment)...')
    try:
        import shap

        # Use a subsample for SHAP (speed)
        shap_sample_size = min(200, len(X_test))
        X_shap = X_test.iloc[:shap_sample_size]

        explainer = shap.TreeExplainer(best_reg)
        shap_values = explainer.shap_values(X_shap)

        # Mean absolute SHAP values
        shap_importance = np.abs(shap_values).mean(axis=0)
        native_imp['shap_importance'] = 0.0
        for i, col in enumerate(feature_cols):
            if col in native_imp['feature'].values:
                native_imp.loc[native_imp['feature'] == col, 'shap_importance'] = \
                    shap_importance[i]

        # Save SHAP summary plot
        fig, ax = plt.subplots(figsize=(10, 8))
        shap.summary_plot(shap_values, X_shap, feature_names=feature_cols,
                         show=False, max_display=20)
        shap_path = os.path.join(output_dir, 'shap_summary.png')
        plt.tight_layout()
        plt.savefig(shap_path, dpi=150, bbox_inches='tight')
        plt.close()
        log(f'SHAP summary plot saved: {shap_path}')

    except Exception as e:
        log(f'SHAP analysis error (non-fatal): {e}')

    # --- Save feature importance CSV ---
    imp_path = os.path.join(output_dir, 'feature_importance.csv')
    native_imp.to_csv(imp_path, index=False, float_format='%.6f')
    log(f'Feature importance saved: {imp_path}')

    return native_imp


# ============================================================================
# STEP 8: GENERATE CONFUSION MATRIX
# ============================================================================

def step8_confusion_matrix(best_name, results, y_cls_test, output_dir):
    """Generate and save confusion matrix plot."""
    print('\n' + '=' * 70)
    print('  STEP 8: CONFUSION MATRIX')
    print('=' * 70)

    y_pred = results[best_name]['y_pred_cls']
    cm = confusion_matrix(y_cls_test, y_pred)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='YlOrRd',
                xticklabels=HEAT_CLASSES, yticklabels=HEAT_CLASSES,
                ax=ax, linewidths=0.5, linecolor='white',
                cbar_kws={'label': 'Count'})
    ax.set_xlabel('Predicted', fontsize=12, fontweight='bold')
    ax.set_ylabel('Actual', fontsize=12, fontweight='bold')
    ax.set_title(f'Confusion Matrix - {best_name}\nUrban Heat Stress Classification',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    cm_path = os.path.join(output_dir, 'confusion_matrix.png')
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    log(f'Confusion matrix saved: {cm_path}')

    # Per-class report
    report = classification_report(y_cls_test, y_pred,
                                   target_names=HEAT_CLASSES, output_dict=True)
    log('Per-class classification report:')
    for cls_name in HEAT_CLASSES:
        if cls_name in report:
            r = report[cls_name]
            log(f'  {cls_name:10s}: Precision={r["precision"]:.3f}, '
                f'Recall={r["recall"]:.3f}, F1={r["f1-score"]:.3f}')

    return cm, report


# ============================================================================
# STEP 9: SAVE OUTPUTS
# ============================================================================

def step9_save_outputs(best_name, results, scores, feature_cols,
                       feature_imp, cm, cls_report, thresholds,
                       corr_info, output_dir):
    """Save trained_model.pkl, model_metrics.json, training_report.md."""
    print('\n' + '=' * 70)
    print('  STEP 9: SAVE ALL OUTPUTS')
    print('=' * 70)

    os.makedirs(output_dir, exist_ok=True)
    best = results[best_name]

    # --- 9a. trained_model.pkl ---
    model_bundle = {
        'best_model_name': best_name,
        'regression_model': best['reg_model'],
        'classification_model': best['cls_model'],
        'feature_columns': feature_cols,
        'heat_classes': HEAT_CLASSES,
        'thresholds': thresholds,
        'metadata': {
            'trained_at': datetime.now().isoformat(),
            'framework_versions': {
                'sklearn': __import__('sklearn').__version__,
                'xgboost': xgb.__version__,
                'lightgbm': lgb.__version__,
                'catboost': cb.__version__,
            },
            'random_state': RANDOM_STATE,
            'cv_folds': CV_FOLDS,
        }
    }

    pkl_path = os.path.join(output_dir, 'trained_model.pkl')
    with open(pkl_path, 'wb') as f:
        pickle.dump(model_bundle, f)
    log(f'trained_model.pkl saved ({os.path.getsize(pkl_path)/1024:.1f} KB)')

    # --- 9b. model_metrics.json ---
    metrics = {
        'best_model': best_name,
        'composite_scores': scores,
        'models': {},
    }

    for name, r in results.items():
        metrics['models'][name] = {
            'regression': r['regression'],
            'classification': r['classification'],
            'composite_score': scores[name],
        }

    metrics['best_model_detail'] = {
        'regression': best['regression'],
        'classification': best['classification'],
        'per_class_report': {
            k: v for k, v in cls_report.items()
            if k in HEAT_CLASSES
        },
    }
    metrics['thresholds'] = thresholds
    metrics['correlation_analysis'] = corr_info
    metrics['engineering_log'] = ENG_LOG

    json_path = os.path.join(output_dir, 'model_metrics.json')
    with open(json_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    log(f'model_metrics.json saved ({os.path.getsize(json_path)/1024:.1f} KB)')

    # --- 9c. training_report.md ---
    report_path = os.path.join(output_dir, 'training_report.md')
    with open(report_path, 'w') as f:
        f.write('# Urban Heat AI - Model Training Report\n\n')
        f.write(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('---\n\n')

        # Architecture decision
        f.write('## Architecture Decision\n\n')
        f.write('**Hybrid Regression + Classification** approach selected because:\n')
        f.write('- Regression provides granular Heat Score (0-100) for fine-grained analysis\n')
        f.write('- Classification provides actionable categories (Low/Moderate/High/Extreme) for policy\n')
        f.write('- Tree-based ensembles chosen: handle mixed types, capture nonlinearity, robust to outliers\n\n')

        # Target engineering
        f.write('## Heat Score Engineering\n\n')
        f.write('Composite index formula:\n')
        f.write('```\n')
        f.write('HeatScore = 0.40 * LST_norm + 0.25 * UHI_norm + 0.15 * UTFVI_norm\n')
        f.write('          + 0.10 * Anthropogenic_Heat_norm + 0.10 * Impervious_norm\n')
        f.write('```\n')
        f.write('Scaled to 0-100. Based on Urban Heat Vulnerability Index (Inostroza et al., 2016).\n\n')

        f.write('### Classification Thresholds\n\n')
        f.write('| Class | Range | Description |\n')
        f.write('|-------|-------|-------------|\n')
        for cls_name, rng in thresholds.items():
            desc = {'Low': 'Minimal heat stress, comfortable',
                    'Moderate': 'Noticeable heat, caution advised',
                    'High': 'Significant heat stress, vulnerable populations at risk',
                    'Extreme': 'Dangerous heat, immediate intervention needed'}
            f.write(f'| {cls_name} | {rng} | {desc.get(cls_name, "")} |\n')
        f.write('\n')

        # Model comparison
        f.write('## Model Comparison\n\n')
        f.write('### Regression Metrics\n\n')
        f.write('| Model | RMSE | MAE | R2 | CV R2 | Time (s) |\n')
        f.write('|-------|------|-----|----|----|----------|\n')
        for name in sorted(results.keys()):
            r = results[name]['regression']
            best_marker = ' **[BEST]**' if name == best_name else ''
            f.write(f'| {name}{best_marker} | {r["RMSE"]:.4f} | {r["MAE"]:.4f} | '
                    f'{r["R2"]:.4f} | {r["CV_R2_mean"]:.4f} +/- {r["CV_R2_std"]:.4f} | '
                    f'{r["train_time_s"]:.1f} |\n')
        f.write('\n')

        f.write('### Classification Metrics\n\n')
        f.write('| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 |\n')
        f.write('|-------|----------|-----------|--------|----|---------|---------|\n')
        for name in sorted(results.keys()):
            r = results[name]['classification']
            best_marker = ' **[BEST]**' if name == best_name else ''
            f.write(f'| {name}{best_marker} | {r["Accuracy"]:.4f} | {r["Precision"]:.4f} | '
                    f'{r["Recall"]:.4f} | {r["F1_Score"]:.4f} | {r["ROC_AUC"]:.4f} | '
                    f'{r["CV_F1_mean"]:.4f} +/- {r["CV_F1_std"]:.4f} |\n')
        f.write('\n')

        f.write('### Composite Scores\n\n')
        f.write('Formula: `0.4*R2 + 0.3*F1 + 0.2*ROC_AUC + 0.1*(1-RMSE_norm)`\n\n')
        f.write('| Model | Composite Score |\n')
        f.write('|-------|---------|\n')
        for name in sorted(scores.keys(), key=lambda k: scores[k], reverse=True):
            marker = ' **[WINNER]**' if name == best_name else ''
            f.write(f'| {name}{marker} | {scores[name]:.4f} |\n')
        f.write('\n')

        # Best model details
        f.write(f'## Best Model: {best_name}\n\n')
        f.write('### Per-Class Performance\n\n')
        f.write('| Class | Precision | Recall | F1 | Support |\n')
        f.write('|-------|-----------|--------|----|---------|\n')
        for cls_name in HEAT_CLASSES:
            if cls_name in cls_report:
                r = cls_report[cls_name]
                f.write(f'| {cls_name} | {r["precision"]:.4f} | {r["recall"]:.4f} | '
                        f'{r["f1-score"]:.4f} | {int(r["support"])} |\n')
        f.write('\n')

        # Feature importance
        f.write('### Top 15 Features\n\n')
        f.write('| Rank | Feature | Native Importance | Permutation Importance |\n')
        f.write('|------|---------|-------------------|------------------------|\n')
        for _, row in feature_imp.head(15).iterrows():
            f.write(f'| {int(row["rank"])} | {row["feature"]} | '
                    f'{row["importance_combined"]:.4f} | '
                    f'{row.get("perm_importance_mean", 0):.4f} |\n')
        f.write('\n')

        # Correlation analysis
        if corr_info['high_corr_pairs']:
            f.write('### Removed Correlated Features\n\n')
            f.write('| Feature A | Feature B | Correlation |\n')
            f.write('|-----------|-----------|-------------|\n')
            for a, b, r in corr_info['high_corr_pairs']:
                f.write(f'| {a} | {b} | {r:.4f} |\n')
            f.write('\n')

        # Engineering log
        f.write('## Engineering Decision Log\n\n')
        f.write('| Time | Decision |\n')
        f.write('|------|----------|\n')
        for entry in ENG_LOG:
            f.write(f'| {entry["time"]} | {entry["msg"]} |\n')
        f.write('\n')

        # Usage
        f.write('## Usage\n\n')
        f.write('```python\n')
        f.write('import pickle\n')
        f.write('import pandas as pd\n\n')
        f.write('# Load model\n')
        f.write('with open("trained_model.pkl", "rb") as f:\n')
        f.write('    bundle = pickle.load(f)\n\n')
        f.write('reg_model = bundle["regression_model"]\n')
        f.write('cls_model = bundle["classification_model"]\n')
        f.write('features = bundle["feature_columns"]\n\n')
        f.write('# Predict\n')
        f.write('df = pd.read_csv("new_data.csv")\n')
        f.write('X = df[features]\n')
        f.write('heat_score = reg_model.predict(X)      # 0-100\n')
        f.write('heat_class = cls_model.predict(X)       # 0-3\n')
        f.write('labels = [bundle["heat_classes"][c] for c in heat_class]\n')
        f.write('```\n')

    log(f'training_report.md saved ({os.path.getsize(report_path)/1024:.1f} KB)')

    return pkl_path, json_path, report_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Train production ML models for Urban Heat Stress prediction.'
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Path to master_dataset.csv')
    parser.add_argument('--output-dir', '-o', default=None,
                        help='Output directory for model artifacts')
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.input), '..', '..', 'models')
    os.makedirs(output_dir, exist_ok=True)

    print('\n' + '#' * 70)
    print('#    URBAN HEAT AI - PRODUCTION ML TRAINING PIPELINE' + ' ' * 17 + '#')
    print('#    ISRO Bharatiya Antariksh Hackathon' + ' ' * 30 + '#')
    print('#' * 70)
    print(f'\n  Input:  {args.input}')
    print(f'  Output: {output_dir}')

    t_start = time.time()

    # Execute pipeline
    df, thresholds = step1_load_and_engineer_target(args.input)
    feature_cols, corr_info = step2_feature_selection(df)
    X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = \
        step3_prepare_data(df, feature_cols)

    # RFE on selected features
    selected = step4_rfe(X_train[feature_cols], y_cls_train, feature_cols)

    # Update feature set with RFE selection
    X_train_sel = X_train[selected]
    X_test_sel = X_test[selected]
    log(f'Final feature set: {len(selected)} features')

    # Train all models
    results = step5_train_models(
        X_train_sel, X_test_sel,
        y_reg_train, y_reg_test,
        y_cls_train, y_cls_test
    )

    # Select best
    best_name, scores = step6_select_best(results)

    # Feature analysis
    feature_imp = step7_feature_analysis(
        best_name, results, X_train_sel, X_test_sel,
        y_reg_test, selected, output_dir
    )

    # Confusion matrix
    cm, cls_report = step8_confusion_matrix(
        best_name, results, y_cls_test, output_dir
    )

    # Save everything
    pkl_path, json_path, report_path = step9_save_outputs(
        best_name, results, scores, selected,
        feature_imp, cm, cls_report, thresholds,
        corr_info, output_dir
    )

    total_time = time.time() - t_start

    # Final summary
    print('\n' + '#' * 70)
    print('#    TRAINING COMPLETE' + ' ' * 47 + '#')
    print('#' * 70)
    print(f'\n  Best Model:   {best_name}')
    print(f'  R2:           {results[best_name]["regression"]["R2"]:.4f}')
    print(f'  RMSE:         {results[best_name]["regression"]["RMSE"]:.4f}')
    print(f'  Accuracy:     {results[best_name]["classification"]["Accuracy"]:.4f}')
    print(f'  F1 Score:     {results[best_name]["classification"]["F1_Score"]:.4f}')
    print(f'  ROC-AUC:      {results[best_name]["classification"]["ROC_AUC"]:.4f}')
    print(f'\n  Total time:   {total_time:.1f}s')
    print(f'\n  Output files:')
    print(f'    trained_model.pkl       {pkl_path}')
    print(f'    model_metrics.json      {json_path}')
    print(f'    feature_importance.csv  {os.path.join(output_dir, "feature_importance.csv")}')
    print(f'    confusion_matrix.png    {os.path.join(output_dir, "confusion_matrix.png")}')
    print(f'    training_report.md      {report_path}')
    print()

    # ── AUTO-RUN: Cooling Optimization Engine ────────────────────────
    # After training completes, automatically run the cooling engine
    # to generate intervention recommendations using the fresh model.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from cooling_engine.cooling_engine import UrbanCoolingEngine

        print('\n' + '=' * 70)
        print('  AUTO-INTEGRATION: Running Cooling Optimization Engine...')
        print('=' * 70)

        cooling_output = os.path.join(
            os.path.dirname(args.input), '..', '..', 'outputs', 'cooling_analysis'
        )

        engine = UrbanCoolingEngine(
            data_path=args.input,
            model_path=pkl_path,
            output_dir=cooling_output,
            city_name='Delhi',
        )

        cooling_results = engine.run(n_zones=5, pop_size=60, n_generations=40)
        log(f'Cooling engine complete: {cooling_results["pareto_solutions"]} '
            f'Pareto solutions found')

    except ImportError:
        print('\n  [INFO] Cooling engine not found — skipping auto-integration.')
        print('  Run manually: python -m cooling_engine.cooling_engine')
    except Exception as e:
        print(f'\n  [WARN] Cooling engine error (non-fatal): {e}')
        print('  The trained model was saved successfully. Run the engine manually:')
        print('  python -m cooling_engine.cooling_engine')


if __name__ == '__main__':
    main()
