# Models

Trained ML model artifacts for Urban Heat Stress prediction.

## Training Pipeline

Run the training pipeline:

```bash
python train_model.py --input ../data/final/master_dataset.csv --output-dir output
```

This trains 6 ensemble models (RandomForest, XGBoost, LightGBM, CatBoost, ExtraTrees, GradientBoosting) for both regression (Heat Score 0-100) and classification (Low/Moderate/High/Extreme), then automatically selects the best model.

## Output Files

| File | Description |
|------|-------------|
| `output/trained_model.pkl` | Best model bundle (regression + classification + feature list) |
| `output/model_metrics.json` | Performance metrics for all 6 models |
| `output/feature_importance.csv` | Native + permutation + SHAP importance rankings |
| `output/confusion_matrix.png` | 4-class confusion matrix heatmap |
| `output/shap_summary.png` | SHAP beeswarm plot for the best model |
| `output/training_report.md` | Full training report with architecture decisions |

## Current Best Model

- **Model**: GradientBoosting
- **R²**: 0.9995 | **RMSE**: 0.4999
- **Accuracy**: 1.0000 | **F1**: 1.0000 | **ROC-AUC**: 1.0000
- **Features**: 10 (selected via RFECV from 37)

## Loading the Model

```python
import pickle
import pandas as pd

with open("output/trained_model.pkl", "rb") as f:
    bundle = pickle.load(f)

reg_model = bundle["regression_model"]
cls_model = bundle["classification_model"]
features = bundle["feature_columns"]

df = pd.read_csv("new_data.csv")
X = df[features]
heat_score = reg_model.predict(X)      # 0-100
heat_class = cls_model.predict(X)       # 0-3
```

## Auto-Integration

After training completes, the pipeline automatically runs the **Cooling Optimization Engine** to generate intervention recommendations using the freshly trained model.
