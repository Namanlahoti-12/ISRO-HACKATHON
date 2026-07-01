# Notebooks

Jupyter notebooks for exploratory data analysis and model evaluation.

## Available Notebooks

> These notebooks are optional companions to the production pipeline (`models/train_model.py`). The full ML training runs as a Python script; notebooks are for interactive exploration.

| Notebook | Description | Status |
|----------|-------------|--------|
| `01_EDA.ipynb` | Exploratory analysis of the master CSV dataset | Planned |
| `02_Feature_Engineering.ipynb` | Additional Python-side feature engineering | Planned |
| `03_Model_Training.ipynb` | ML model training (interactive version) | Planned |
| `04_Evaluation.ipynb` | Model evaluation and UHI hotspot mapping | Planned |
| `05_Cooling_Analysis.ipynb` | Cooling intervention analysis and visualization | Planned |

## Note

The production ML pipeline runs entirely from `models/train_model.py` and does not require Jupyter. The Cooling Optimization Engine runs from `cooling_engine/cooling_engine.py`. These notebooks serve as interactive companions for deeper analysis.
