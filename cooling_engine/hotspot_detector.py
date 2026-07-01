"""
Hotspot Detector — UHI Hotspot Detection and Classification
==============================================================
Detects urban heat island hotspots from the trained model's predictions
and analyzes their feature profiles for intervention planning.

Uses the trained GradientBoosting model to identify areas with:
  - Extreme heat scores (>75th percentile)
  - High heat scores (50th-75th percentile)
and characterizes each hotspot by its contributing features.
"""

import os
import pickle
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')


# Feature groups for hotspot characterization
FEATURE_GROUPS = {
    'spectral': ['LST', 'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo'],
    'land_cover': ['LULC_ESA', 'LULC_DW', 'Impervious_Frac', 'Tree_Cover_Pct'],
    'weather': ['AirTemp', 'Humidity', 'WindSpeed', 'WindDirection',
                'SolarRadiation', 'Cloud_Cover_Proxy', 'Pressure', 'Rainfall'],
    'terrain': ['Elevation', 'Slope', 'Aspect'],
    'urban': ['Building_Density', 'Building_Height', 'Building_Volume',
              'Road_Density_Proxy', 'Street_Width_Proxy', 'Nighttime_Lights',
              'Population_Density'],
    'distance': ['Dist_Water', 'Dist_Green'],
    'derived': ['Green_Space_Density', 'Surface_Roughness',
                'Anthropogenic_Heat', 'UHI_Intensity', 'UTFVI',
                'UTCI_Approx'],
}

ALL_ANALYSIS_FEATURES = [
    'LST', 'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'Albedo',
    'LULC_ESA', 'Impervious_Frac', 'Building_Density', 'Building_Height',
    'Road_Density_Proxy', 'Population_Density', 'Tree_Cover_Pct',
    'Dist_Water', 'Dist_Green', 'Elevation', 'Slope',
    'AirTemp', 'Humidity', 'WindSpeed', 'WindDirection',
    'SolarRadiation', 'Cloud_Cover_Proxy', 'Nighttime_Lights',
    'Anthropogenic_Heat', 'UHI_Intensity', 'UTFVI', 'UTCI_Approx',
    'Surface_Roughness', 'Building_Volume', 'Green_Space_Density',
]


class HotspotDetector:
    """
    Detects and characterizes UHI hotspots using the trained model.

    The detector:
    1. Loads the trained model bundle (trained_model.pkl)
    2. Predicts Heat Scores for all pixels
    3. Identifies hotspots (High + Extreme class)
    4. Profiles each hotspot by its feature values
    5. Ranks hotspots by severity and intervention priority
    """

    def __init__(self, model_path: str = None):
        """
        Initialize the hotspot detector.

        Args:
            model_path: Path to trained_model.pkl. If None, uses default location.
        """
        self.model_path = model_path
        self.model_bundle = None
        self.reg_model = None
        self.cls_model = None
        self.feature_columns = None
        self.heat_classes = None
        self.thresholds = None

    def load_model(self, model_path: str = None):
        """Load the trained model bundle."""
        path = model_path or self.model_path
        if path is None:
            # Default path relative to this file
            path = os.path.join(
                os.path.dirname(__file__), '..', 'models', 'output',
                'trained_model.pkl'
            )

        with open(path, 'rb') as f:
            self.model_bundle = pickle.load(f)

        self.reg_model = self.model_bundle['regression_model']
        self.cls_model = self.model_bundle['classification_model']
        self.feature_columns = self.model_bundle['feature_columns']
        self.heat_classes = self.model_bundle['heat_classes']
        self.thresholds = self.model_bundle.get('thresholds', {})

        print(f'  [OK] Model loaded: {self.model_bundle["best_model_name"]}')
        print(f'  [OK] Features: {len(self.feature_columns)} '
              f'({", ".join(self.feature_columns[:5])}...)')
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run predictions on the dataset.

        Args:
            df: DataFrame with feature columns matching the trained model.

        Returns:
            DataFrame with added columns:
                - HeatScore_Predicted: continuous 0-100
                - HeatClass_Predicted: 0-3 (Low/Moderate/High/Extreme)
                - HeatClass_Label: string label
        """
        if self.reg_model is None:
            self.load_model()

        # Select model features from the dataframe
        available = [c for c in self.feature_columns if c in df.columns]
        missing = [c for c in self.feature_columns if c not in df.columns]

        if missing:
            print(f'  [WARN] Missing {len(missing)} model features: {missing}')
            # Fill missing with 0 (fallback)
            for col in missing:
                df[col] = 0.0

        X = df[self.feature_columns].copy()

        # Handle NaN
        nan_cols = X.columns[X.isna().any()].tolist()
        if nan_cols:
            X = X.fillna(X.median())

        # Predict
        df = df.copy()
        df['HeatScore_Predicted'] = self.reg_model.predict(X).clip(0, 100).round(2)
        df['HeatClass_Predicted'] = self.cls_model.predict(X)
        df['HeatClass_Label'] = df['HeatClass_Predicted'].map(
            {i: name for i, name in enumerate(self.heat_classes)}
        )

        return df

    def detect_hotspots(self, df: pd.DataFrame,
                        min_class: int = 2,
                        percentile_threshold: float = None) -> pd.DataFrame:
        """
        Detect hotspot pixels from predictions.

        Args:
            df: DataFrame with predictions (from self.predict())
            min_class: Minimum heat class to consider as hotspot (2=High, 3=Extreme)
            percentile_threshold: Alternative: use top N percentile of HeatScore

        Returns:
            DataFrame containing only hotspot rows, sorted by severity.
        """
        if 'HeatScore_Predicted' not in df.columns:
            df = self.predict(df)

        if percentile_threshold is not None:
            cutoff = np.percentile(df['HeatScore_Predicted'], percentile_threshold)
            hotspots = df[df['HeatScore_Predicted'] >= cutoff].copy()
        else:
            hotspots = df[df['HeatClass_Predicted'] >= min_class].copy()

        hotspots = hotspots.sort_values('HeatScore_Predicted', ascending=False)

        print(f'  [OK] Detected {len(hotspots)} hotspot pixels '
              f'({len(hotspots)/len(df)*100:.1f}% of total)')

        # Class breakdown
        if 'HeatClass_Label' in hotspots.columns:
            for label in hotspots['HeatClass_Label'].unique():
                count = (hotspots['HeatClass_Label'] == label).sum()
                print(f'       {label}: {count} pixels')

        return hotspots

    def profile_hotspots(self, hotspots: pd.DataFrame,
                         full_dataset: pd.DataFrame) -> Dict:
        """
        Characterize hotspot features relative to the full dataset.

        Returns a dictionary with:
            - hotspot_stats: Mean/std of each feature in hotspots
            - city_stats: Mean/std of each feature in full dataset
            - deviation: How much hotspot features deviate from city mean
            - contributing_factors: Ranked list of features contributing to heat
            - vulnerability_profile: Summary of key vulnerabilities
        """
        profile = {
            'n_hotspots': len(hotspots),
            'n_total': len(full_dataset),
            'hotspot_fraction': round(len(hotspots) / len(full_dataset), 4),
            'avg_heat_score': round(hotspots['HeatScore_Predicted'].mean(), 2),
            'max_heat_score': round(hotspots['HeatScore_Predicted'].max(), 2),
            'feature_analysis': {},
            'contributing_factors': [],
            'vulnerability_profile': {},
        }

        # Analyze each feature available in both datasets
        features_to_analyze = [f for f in ALL_ANALYSIS_FEATURES
                               if f in hotspots.columns and f in full_dataset.columns]

        for feat in features_to_analyze:
            hs_mean = hotspots[feat].mean()
            hs_std = hotspots[feat].std()
            city_mean = full_dataset[feat].mean()
            city_std = full_dataset[feat].std()

            # Z-score deviation of hotspot mean from city mean
            deviation = (hs_mean - city_mean) / city_std if city_std > 0 else 0

            profile['feature_analysis'][feat] = {
                'hotspot_mean': round(float(hs_mean), 4),
                'hotspot_std': round(float(hs_std), 4),
                'city_mean': round(float(city_mean), 4),
                'city_std': round(float(city_std), 4),
                'deviation_zscore': round(float(deviation), 4),
                'direction': 'higher' if deviation > 0 else 'lower',
            }

        # Rank contributing factors by absolute deviation
        sorted_factors = sorted(
            profile['feature_analysis'].items(),
            key=lambda x: abs(x[1]['deviation_zscore']),
            reverse=True
        )
        profile['contributing_factors'] = [
            {
                'feature': feat,
                'deviation': info['deviation_zscore'],
                'direction': info['direction'],
                'hotspot_mean': info['hotspot_mean'],
                'city_mean': info['city_mean'],
            }
            for feat, info in sorted_factors[:15]
        ]

        # Vulnerability profile — key indicators
        vp = {}
        fa = profile['feature_analysis']

        if 'NDVI' in fa:
            vp['vegetation_deficit'] = fa['NDVI']['deviation_zscore'] < -0.5
        if 'Impervious_Frac' in fa:
            vp['high_imperviousness'] = fa['Impervious_Frac']['deviation_zscore'] > 0.5
        if 'Building_Density' in fa:
            vp['high_building_density'] = fa['Building_Density']['deviation_zscore'] > 0.5
        if 'Dist_Green' in fa:
            vp['far_from_green_space'] = fa['Dist_Green']['deviation_zscore'] > 0.5
        if 'Dist_Water' in fa:
            vp['far_from_water'] = fa['Dist_Water']['deviation_zscore'] > 0.5
        if 'Albedo' in fa:
            vp['low_albedo'] = fa['Albedo']['deviation_zscore'] < -0.3
        if 'WindSpeed' in fa:
            vp['low_wind'] = fa['WindSpeed']['deviation_zscore'] < -0.3
        if 'Tree_Cover_Pct' in fa:
            vp['low_tree_cover'] = fa['Tree_Cover_Pct']['deviation_zscore'] < -0.3
        if 'Population_Density' in fa:
            vp['high_population'] = fa['Population_Density']['deviation_zscore'] > 0.5
        if 'Anthropogenic_Heat' in fa:
            vp['high_anthro_heat'] = fa['Anthropogenic_Heat']['deviation_zscore'] > 0.5

        profile['vulnerability_profile'] = vp

        return profile

    def cluster_hotspots(self, hotspots: pd.DataFrame,
                         n_clusters: int = 5) -> pd.DataFrame:
        """
        Group hotspot pixels into spatial clusters (intervention zones).

        Uses KMeans on (Latitude, Longitude) to group nearby hotspot pixels.
        Each cluster represents a potential intervention zone.

        Args:
            hotspots: DataFrame of hotspot pixels with Latitude/Longitude
            n_clusters: Number of clusters (intervention zones)

        Returns:
            DataFrame with added 'Zone_ID' column
        """
        from sklearn.cluster import KMeans

        if 'Latitude' not in hotspots.columns or 'Longitude' not in hotspots.columns:
            print('  [WARN] Lat/Lon not available, assigning sequential zone IDs')
            hotspots = hotspots.copy()
            # Divide into zones by heat score quantiles
            hotspots['Zone_ID'] = pd.qcut(
                hotspots['HeatScore_Predicted'],
                q=min(n_clusters, len(hotspots)),
                labels=False, duplicates='drop'
            )
            return hotspots

        coords = hotspots[['Latitude', 'Longitude']].values
        n_clusters = min(n_clusters, len(hotspots))

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        hotspots = hotspots.copy()
        hotspots['Zone_ID'] = kmeans.fit_predict(coords)

        # Print zone summary
        for zone_id in range(n_clusters):
            zone = hotspots[hotspots['Zone_ID'] == zone_id]
            print(f'  Zone {zone_id}: {len(zone)} pixels, '
                  f'avg HeatScore={zone["HeatScore_Predicted"].mean():.1f}')

        return hotspots

    def get_zone_profiles(self, hotspots: pd.DataFrame,
                          full_dataset: pd.DataFrame) -> Dict:
        """
        Profile each hotspot zone separately for targeted interventions.

        Returns a dict mapping Zone_ID → profile dict.
        """
        if 'Zone_ID' not in hotspots.columns:
            hotspots = self.cluster_hotspots(hotspots)

        zone_profiles = {}
        for zone_id in sorted(hotspots['Zone_ID'].unique()):
            zone_pixels = hotspots[hotspots['Zone_ID'] == zone_id]
            zone_profiles[int(zone_id)] = self.profile_hotspots(
                zone_pixels, full_dataset
            )
            zone_profiles[int(zone_id)]['zone_id'] = int(zone_id)

            if 'Latitude' in zone_pixels.columns:
                zone_profiles[int(zone_id)]['centroid'] = {
                    'lat': round(zone_pixels['Latitude'].mean(), 6),
                    'lon': round(zone_pixels['Longitude'].mean(), 6),
                }

        return zone_profiles


def run_detection_pipeline(data_path: str, model_path: str = None,
                           n_zones: int = 5) -> Tuple[pd.DataFrame, Dict]:
    """
    Complete hotspot detection pipeline.

    Args:
        data_path: Path to master_dataset.csv
        model_path: Path to trained_model.pkl (optional)
        n_zones: Number of intervention zones

    Returns:
        Tuple of (hotspot_dataframe, zone_profiles_dict)
    """
    print('\n' + '=' * 70)
    print('  HOTSPOT DETECTION PIPELINE')
    print('=' * 70)

    # Load data
    df = pd.read_csv(data_path)
    print(f'  [OK] Loaded dataset: {df.shape[0]} rows × {df.shape[1]} cols')

    # Initialize detector
    detector = HotspotDetector(model_path)
    detector.load_model()

    # Predict
    print('\n  Running predictions...')
    df = detector.predict(df)

    # Detect hotspots
    print('\n  Detecting hotspots...')
    hotspots = detector.detect_hotspots(df, min_class=2)

    # Cluster into zones
    print('\n  Clustering into intervention zones...')
    hotspots = detector.cluster_hotspots(hotspots, n_clusters=n_zones)

    # Profile each zone
    print('\n  Profiling hotspot zones...')
    zone_profiles = detector.get_zone_profiles(hotspots, df)

    return hotspots, zone_profiles, df


if __name__ == '__main__':
    import sys

    data_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), '..', 'data', 'final', 'master_dataset.csv'
    )

    hotspots, profiles, full = run_detection_pipeline(data_path)

    print('\n' + '=' * 70)
    print('  DETECTION COMPLETE')
    print('=' * 70)
    print(f'  Total hotspot pixels: {len(hotspots)}')
    print(f'  Zones identified: {len(profiles)}')
    for zid, p in profiles.items():
        print(f'  Zone {zid}: {p["n_hotspots"]} pixels, '
              f'avg score={p["avg_heat_score"]:.1f}, '
              f'vulnerabilities={sum(p["vulnerability_profile"].values())}')
