# Installation & Setup Guide

Complete setup instructions for the Urban Heat AI project.

---

## Prerequisites

| Requirement | How to Get |
|-------------|-----------|
| **Google Earth Engine account** | [Sign up (free for research)](https://earthengine.google.com/signup/) |
| **Google Drive** | ~5 GB free space for exported files |
| **Python 3.8+** | [Download Python](https://www.python.org/downloads/) |
| **Web browser** | Chrome recommended for GEE Code Editor |

---

## Step 1: Google Earth Engine Setup

### 1a. Create a GEE Account
1. Go to [https://earthengine.google.com/signup/](https://earthengine.google.com/signup/)
2. Sign in with your Google account
3. Fill out the registration form
4. Wait for approval (usually instant for research/education)

### 1b. Verify Access
1. Open [https://code.earthengine.google.com](https://code.earthengine.google.com)
2. You should see the Code Editor with a script panel, map, and console
3. If you see "Access Denied", your registration is still pending

---

## Step 2: Run the GEE Pipeline

### 2a. Open the Script
1. In GEE Code Editor, click **File → New**
2. Open the file `gee/main.js` from this project on your computer
3. Select all contents (Ctrl+A) and copy (Ctrl+C)
4. Paste into the GEE script editor (Ctrl+V)

### 2b. Configure Your City
Find Section 1 at the top of the script (approximately lines 30–60).

Change these values for your target city:

```javascript
var CITY_NAME       = 'Mumbai';      // Your city name
var CENTER_LAT      = 19.0760;       // Latitude (from Google Maps)
var CENTER_LON      = 72.8777;       // Longitude (from Google Maps)
var BUFFER_RADIUS_M = 25000;         // Study area radius in meters
```

**How to find coordinates:**
1. Open [Google Maps](https://maps.google.com)
2. Right-click on your city center
3. Click the coordinates that appear — they'll be copied
4. Paste into the script (format: latitude, longitude)

### 2c. Run the Script
1. Click the **Run** button (top of editor)
2. Wait for the script to execute (~30–60 seconds)
3. Check the **Console** panel for status messages
4. The map should display layers (LST, UHI Intensity visible by default)

### 2d. Export Data
1. Click the **Tasks** tab (top-right of the editor)
2. You'll see 34 export tasks (33 GeoTIFFs + 1 CSV)
3. Click **Run** on each task (or use "Run All" if available)
4. Tasks process on Google's servers — takes 10–30 minutes
5. Files appear in Google Drive under the folder `ISRO_UHI_Data`

---

## Step 3: Download Data from Google Drive

1. Open [Google Drive](https://drive.google.com)
2. Navigate to the `ISRO_UHI_Data` folder
3. Download all files
4. Place GeoTIFF files in `data/raw/`
5. Place the CSV file in `data/final/`

---

## Step 4: Python Environment Setup

### 4a. Install Dependencies

```bash
cd UrbanHeatAI
pip install -r requirements.txt
```

This installs:
- `numpy` — numerical computing
- `pandas` — data manipulation
- `scikit-learn` — machine learning utilities

### 4b. Validate and Prepare Data

```bash
python utils/data_validator.py --input data/final/Delhi_UHI_MasterDataset.csv
```

This will:
- Validate all 37 columns exist
- Check value ranges are sensible
- Remove any invalid rows
- One-hot encode LULC categorical columns
- Split into train/validation/test sets (70/10/20)
- Generate a quality report JSON

### 4c. Output Files

After running the validator, you'll have:

```
data/final/
├── Delhi_UHI_MasterDataset.csv    # Original from GEE
├── Delhi_train.csv                # 70% training set
├── Delhi_val.csv                  # 10% validation set
├── Delhi_test.csv                 # 20% test set
└── quality_report.json            # Data quality metrics
```

---

## Step 5: Quick ML Start (Preview)

```python
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Load data
train = pd.read_csv('data/final/Delhi_train.csv')
test = pd.read_csv('data/final/Delhi_test.csv')

# Separate features and target
X_train = train.drop(columns=['LST'])
y_train = train['LST']
X_test = test.drop(columns=['LST'])
y_test = test['LST']

# Train a quick model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(f"MAE: {mean_absolute_error(y_test, y_pred):.2f} C")
print(f"R2:  {r2_score(y_test, y_pred):.4f}")
```

---

## Troubleshooting

### GEE Issues

| Problem | Solution |
|---------|----------|
| "Cannot read property of null" | Your date range has no images. Try widening the date range or reducing `MAX_CLOUD_PERCENT` threshold. |
| "Computation timed out" | Reduce `BUFFER_RADIUS_M` (try 15000 instead of 25000) or increase `EXPORT_SCALE` (try 100). |
| Export task fails | Check the error message in Tasks tab. Usually means the region is too large or a dataset is unavailable for your area. |
| Empty map layers | Check Console for error messages. Verify your lat/lon are correct (common mistake: swapping lat and lon). |
| "Collection.first() — empty collection" | No images match your filters. Check city bounds and date range. |

### Python Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: numpy` | Run `pip install -r requirements.txt` |
| CSV has missing columns | Check that your GEE export completed fully. Re-run the main.js script. |
| `UnicodeEncodeError` | The validator uses ASCII-safe output. If you still see encoding errors, run with `python -u` flag. |

---

## Indian City Coordinates Reference

| City | Latitude | Longitude | Recommended Buffer (m) |
|------|----------|-----------|----------------------|
| Delhi | 28.6139 | 77.2090 | 25000 |
| Mumbai | 19.0760 | 72.8777 | 25000 |
| Bangalore | 12.9716 | 77.5946 | 20000 |
| Chennai | 13.0827 | 80.2707 | 20000 |
| Hyderabad | 17.3850 | 78.4867 | 20000 |
| Kolkata | 22.5726 | 88.3639 | 20000 |
| Pune | 18.5204 | 73.8567 | 15000 |
| Ahmedabad | 23.0225 | 72.5714 | 20000 |
| Jaipur | 26.9124 | 75.7873 | 15000 |
| Lucknow | 26.8467 | 80.9462 | 15000 |
| Nagpur | 21.1458 | 79.0882 | 15000 |
| Bhopal | 23.2599 | 77.4126 | 15000 |
| Varanasi | 25.3176 | 82.9739 | 10000 |
| Chandigarh | 30.7333 | 76.7794 | 10000 |
