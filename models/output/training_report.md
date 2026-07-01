# Urban Heat AI - Model Training Report

Generated: 2026-06-29 18:26:44

---

## Architecture Decision

**Hybrid Regression + Classification** approach selected because:
- Regression provides granular Heat Score (0-100) for fine-grained analysis
- Classification provides actionable categories (Low/Moderate/High/Extreme) for policy
- Tree-based ensembles chosen: handle mixed types, capture nonlinearity, robust to outliers

## Heat Score Engineering

Composite index formula:
```
HeatScore = 0.40 * LST_norm + 0.25 * UHI_norm + 0.15 * UTFVI_norm
          + 0.10 * Anthropogenic_Heat_norm + 0.10 * Impervious_norm
```
Scaled to 0-100. Based on Urban Heat Vulnerability Index (Inostroza et al., 2016).

### Classification Thresholds

| Class | Range | Description |
|-------|-------|-------------|
| Low | < 27.9 | Minimal heat stress, comfortable |
| Moderate | 27.9 - 35.8 | Noticeable heat, caution advised |
| High | 35.8 - 45.1 | Significant heat stress, vulnerable populations at risk |
| Extreme | >= 45.1 | Dangerous heat, immediate intervention needed |

## Model Comparison

### Regression Metrics

| Model | RMSE | MAE | R2 | CV R2 | Time (s) |
|-------|------|-----|----|----|----------|
| CatBoost | 0.5580 | 0.3656 | 0.9988 | 0.9962 +/- 0.0018 | 2.0 |
| ExtraTrees | 2.5933 | 2.0374 | 0.9749 | 0.9662 +/- 0.0055 | 0.3 |
| GradientBoosting **[BEST]** | 0.3590 | 0.1752 | 0.9995 | 0.9985 +/- 0.0010 | 1.3 |
| LightGBM | 0.8007 | 0.5091 | 0.9976 | 0.9951 +/- 0.0017 | 0.5 |
| RandomForest | 1.7349 | 1.0984 | 0.9888 | 0.9827 +/- 0.0054 | 0.6 |
| XGBoost | 0.6596 | 0.4656 | 0.9984 | 0.9963 +/- 0.0014 | 0.7 |

### Classification Metrics

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 |
|-------|----------|-----------|--------|----|---------|---------|
| CatBoost | 0.9893 | 0.9893 | 0.9893 | 0.9893 | 0.9997 | 0.9812 +/- 0.0066 |
| ExtraTrees | 0.9519 | 0.9526 | 0.9519 | 0.9521 | 0.9967 | 0.9393 +/- 0.0151 |
| GradientBoosting **[BEST]** | 0.9920 | 0.9920 | 0.9920 | 0.9920 | 0.9987 | 0.9813 +/- 0.0096 |
| LightGBM | 0.9840 | 0.9841 | 0.9840 | 0.9840 | 0.9991 | 0.9813 +/- 0.0084 |
| RandomForest | 0.9706 | 0.9712 | 0.9706 | 0.9706 | 0.9990 | 0.9726 +/- 0.0065 |
| XGBoost | 0.9866 | 0.9868 | 0.9866 | 0.9867 | 0.9992 | 0.9813 +/- 0.0054 |

### Composite Scores

Formula: `0.4*R2 + 0.3*F1 + 0.2*ROC_AUC + 0.1*(1-RMSE_norm)`

| Model | Composite Score |
|-------|---------|
| GradientBoosting **[WINNER]** | 0.9833 |
| CatBoost | 0.9747 |
| XGBoost | 0.9698 |
| LightGBM | 0.9632 |
| RandomForest | 0.9196 |
| ExtraTrees | 0.8749 |

## Best Model: GradientBoosting

### Per-Class Performance

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| Low | 0.9894 | 0.9894 | 0.9894 | 94 |
| Moderate | 0.9892 | 0.9892 | 0.9892 | 93 |
| High | 0.9894 | 1.0000 | 0.9947 | 93 |
| Extreme | 1.0000 | 0.9894 | 0.9947 | 94 |

### Top 15 Features

| Rank | Feature | Native Importance | Permutation Importance |
|------|---------|-------------------|------------------------|
| 1 | UHI_Intensity | 0.8446 | 0.0032 |
| 2 | Anthropogenic_Heat | 0.0604 | -0.0000 |
| 3 | Building_Density | 0.0439 | -0.0000 |
| 4 | Building_Volume | 0.0226 | 0.0011 |
| 5 | NDBI | 0.0137 | 0.0060 |
| 6 | Population_Density | 0.0103 | 0.0044 |
| 7 | Nighttime_Lights | 0.0039 | 0.0000 |
| 8 | MNDWI | 0.0003 | 0.0008 |
| 9 | Dist_Green | 0.0003 | 1.3980 |
| 10 | LULC_ESA | 0.0001 | 0.0317 |

### Removed Correlated Features

| Feature A | Feature B | Correlation |
|-----------|-----------|-------------|
| MNDWI | NDWI | 0.9742 |
| SAVI | NDVI | 1.0000 |
| Street_Width_Proxy | Road_Density_Proxy | 0.9692 |
| Cloud_Cover_Proxy | SolarRadiation | 1.0000 |
| UTFVI | UHI_Intensity | 1.0000 |
| LULC_ESA_Built_up | Impervious_Frac | 1.0000 |

## Engineering Decision Log

| Time | Decision |
|------|----------|
| 18:25:01 | Loaded UrbanHeatAI\data\final\master_dataset.csv: 1869 rows x 92 cols |
| 18:25:01 | HeatScore component: LST (weight=0.40) - primary surface temperature |
| 18:25:01 | HeatScore component: UHI_Intensity (weight=0.25) - urban heat island effect |
| 18:25:01 | HeatScore component: UTFVI (weight=0.15) - thermal field variance |
| 18:25:01 | HeatScore component: Anthropogenic_Heat (weight=0.10) - waste heat proxy |
| 18:25:01 | HeatScore component: Impervious_Frac (weight=0.10) - sealed surfaces |
| 18:25:01 | HeatScore range: 0.6 - 99.6 (mean=38.5, std=16.0) |
| 18:25:01 | Classification thresholds: Low<27.9, Moderate<35.8, High<45.1, Extreme>=45.1 |
| 18:25:01 | Class distribution: {0: np.int64(468), 1: np.int64(467), 2: np.int64(467), 3: np.int64(467)} |
| 18:25:01 | Starting features: 87 |
| 18:25:01 | DECISION: Using 52 raw features (tree models dont need normalization). Excluded 35 normalized duplicates. |
| 18:25:01 | Running Pearson correlation analysis... |
| 18:25:01 | Removed 6 highly correlated features (r>0.95): {'Road_Density_Proxy', 'UTFVI', 'NDWI', 'NDVI', 'Cloud_Cover_Proxy', 'Impervious_Frac'} |
| 18:25:01 |   Corr pair: MNDWI <-> NDWI (r=0.9742) |
| 18:25:01 |   Corr pair: SAVI <-> NDVI (r=1.0) |
| 18:25:01 |   Corr pair: Street_Width_Proxy <-> Road_Density_Proxy (r=0.9692) |
| 18:25:01 |   Corr pair: Cloud_Cover_Proxy <-> SolarRadiation (r=1.0) |
| 18:25:01 |   Corr pair: UTFVI <-> UHI_Intensity (r=1.0) |
| 18:25:01 |   Corr pair: LULC_ESA_Built_up <-> Impervious_Frac (r=1.0) |
| 18:25:01 | Features after correlation filter: 46 |
| 18:25:01 | Train: 1495 samples | Test: 374 samples |
| 18:25:01 | Train class distribution: {0: np.int64(374), 1: np.int64(374), 2: np.int64(374), 3: np.int64(373)} |
| 18:25:01 | Test class distribution:  {0: np.int64(94), 1: np.int64(93), 2: np.int64(93), 3: np.int64(94)} |
| 18:25:01 | Running RFECV (this may take a few minutes)... |
| 18:25:33 | RFECV optimal features: 10 out of 46 |
| 18:25:33 | RFECV best CV score: 0.9726 |
| 18:25:33 | Selected features: ['NDBI', 'MNDWI', 'LULC_ESA', 'Population_Density', 'Building_Density', 'Building_Volume', 'Dist_Green', 'Nighttime_Lights', 'UHI_Intensity', 'Anthropogenic_Heat'] |
| 18:25:33 | Final feature set: 10 features |
| 18:25:38 | RandomForest REG: RMSE=1.735, MAE=1.098, R2=0.9888, CV_R2=0.9827+-0.0054, Time=0.6s |
| 18:25:43 | RandomForest CLS: Acc=0.9706, F1=0.9706, ROC-AUC=0.9990, CV_F1=0.9726+-0.0065, Time=0.7s |
| 18:25:47 | XGBoost REG: RMSE=0.660, MAE=0.466, R2=0.9984, CV_R2=0.9963+-0.0014, Time=0.7s |
| 18:25:49 | XGBoost CLS: Acc=0.9866, F1=0.9867, ROC-AUC=0.9992, CV_F1=0.9813+-0.0054, Time=0.9s |
| 18:25:51 | LightGBM REG: RMSE=0.801, MAE=0.509, R2=0.9976, CV_R2=0.9951+-0.0017, Time=0.5s |
| 18:25:55 | LightGBM CLS: Acc=0.9840, F1=0.9840, ROC-AUC=0.9991, CV_F1=0.9813+-0.0084, Time=0.8s |
| 18:26:02 | CatBoost REG: RMSE=0.558, MAE=0.366, R2=0.9988, CV_R2=0.9962+-0.0018, Time=2.0s |
| 18:26:24 | CatBoost CLS: Acc=0.9893, F1=0.9893, ROC-AUC=0.9997, CV_F1=0.9812+-0.0066, Time=6.2s |
| 18:26:25 | ExtraTrees REG: RMSE=2.593, MAE=2.037, R2=0.9749, CV_R2=0.9662+-0.0055, Time=0.3s |
| 18:26:27 | ExtraTrees CLS: Acc=0.9519, F1=0.9521, ROC-AUC=0.9967, CV_F1=0.9393+-0.0151, Time=0.5s |
| 18:26:29 | GradientBoosting REG: RMSE=0.359, MAE=0.175, R2=0.9995, CV_R2=0.9985+-0.0010, Time=1.3s |
| 18:26:40 | GradientBoosting CLS: Acc=0.9920, F1=0.9920, ROC-AUC=0.9987, CV_F1=0.9813+-0.0096, Time=5.2s |
| 18:26:40 | RandomForest: Composite=0.9196 (R2=0.989, F1=0.971, ROC=0.999) |
| 18:26:40 | XGBoost: Composite=0.9698 (R2=0.998, F1=0.987, ROC=0.999) |
| 18:26:40 | LightGBM: Composite=0.9632 (R2=0.998, F1=0.984, ROC=0.999) |
| 18:26:40 | CatBoost: Composite=0.9747 (R2=0.999, F1=0.989, ROC=1.000) |
| 18:26:40 | ExtraTrees: Composite=0.8749 (R2=0.975, F1=0.952, ROC=0.997) |
| 18:26:40 | GradientBoosting: Composite=0.9833 (R2=1.000, F1=0.992, ROC=0.999) |
| 18:26:40 | BEST MODEL: GradientBoosting (composite score = 0.9833) |
| 18:26:40 | Top 10 features by native importance: |
| 18:26:40 |    1. UHI_Intensity: 0.8446 |
| 18:26:40 |    2. Anthropogenic_Heat: 0.0604 |
| 18:26:40 |    3. Building_Density: 0.0439 |
| 18:26:40 |    4. Building_Volume: 0.0226 |
| 18:26:40 |    5. NDBI: 0.0137 |
| 18:26:40 |    6. Population_Density: 0.0103 |
| 18:26:40 |    7. Nighttime_Lights: 0.0039 |
| 18:26:40 |    8. MNDWI: 0.0003 |
| 18:26:40 |    9. Dist_Green: 0.0003 |
| 18:26:40 |   10. LULC_ESA: 0.0001 |
| 18:26:40 | Computing permutation importance (regression model)... |
| 18:26:40 | Top 10 by permutation importance: |
| 18:26:40 |   Dist_Green: 1.3980 +/- 0.0996 |
| 18:26:40 |   LULC_ESA: 0.0317 +/- 0.0020 |
| 18:26:40 |   NDBI: 0.0060 +/- 0.0004 |
| 18:26:40 |   Population_Density: 0.0044 +/- 0.0004 |
| 18:26:40 |   UHI_Intensity: 0.0032 +/- 0.0003 |
| 18:26:40 |   Building_Volume: 0.0011 +/- 0.0001 |
| 18:26:40 |   MNDWI: 0.0008 +/- 0.0002 |
| 18:26:40 |   Nighttime_Lights: 0.0000 +/- 0.0000 |
| 18:26:40 |   Building_Density: -0.0000 +/- 0.0000 |
| 18:26:40 |   Anthropogenic_Heat: -0.0000 +/- 0.0000 |
| 18:26:40 | Computing SHAP values (this may take a moment)... |
| 18:26:44 | SHAP summary plot saved: UrbanHeatAI\models\output\shap_summary.png |
| 18:26:44 | Feature importance saved: UrbanHeatAI\models\output\feature_importance.csv |
| 18:26:44 | Confusion matrix saved: UrbanHeatAI\models\output\confusion_matrix.png |
| 18:26:44 | Per-class classification report: |
| 18:26:44 |   Low       : Precision=0.989, Recall=0.989, F1=0.989 |
| 18:26:44 |   Moderate  : Precision=0.989, Recall=0.989, F1=0.989 |
| 18:26:44 |   High      : Precision=0.989, Recall=1.000, F1=0.995 |
| 18:26:44 |   Extreme   : Precision=1.000, Recall=0.989, F1=0.995 |
| 18:26:44 | trained_model.pkl saved (4400.5 KB) |
| 18:26:44 | model_metrics.json saved (14.3 KB) |

## Usage

```python
import pickle
import pandas as pd

# Load model
with open("trained_model.pkl", "rb") as f:
    bundle = pickle.load(f)

reg_model = bundle["regression_model"]
cls_model = bundle["classification_model"]
features = bundle["feature_columns"]

# Predict
df = pd.read_csv("new_data.csv")
X = df[features]
heat_score = reg_model.predict(X)      # 0-100
heat_class = cls_model.predict(X)       # 0-3
labels = [bundle["heat_classes"][c] for c in heat_class]
```
