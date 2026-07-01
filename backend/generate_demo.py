import os
import json
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize

def create_demo_rasters():
    print("[DEMO] Generating synthetic India-wide rasters...")
    project_root = os.path.dirname(__file__)
    geojson_path = os.path.join(project_root, 'india.geojson')
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Get all geometries as GeoJSON dicts
    geometries = [feature['geometry'] for feature in data.get('features', [])]
        
    bounds = (68.1, 6.7, 97.4, 35.5) # India approx bounds
    width, height = 1000, 1000
    transform = from_bounds(*bounds, width, height)
    
    mask = rasterize(
        [(geom, 1) for geom in geometries],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        all_touched=True,
        dtype=np.uint8
    )
    
    # Create spatial coordinates for gradients
    y, x = np.mgrid[0:height, 0:width]
    # Normalize 0 to 1
    yn = y / height
    xn = x / width
    
    # Distance functions for procedural generation
    dist_nw = np.sqrt((xn - 0.2)**2 + (yn - 0.2)**2)
    dist_ne = np.sqrt((xn - 0.8)**2 + (yn - 0.1)**2)
    dist_ganga = np.sqrt((xn - 0.5)**2 + (yn - 0.3)**2)
    
    # Layers definition (base value, noise scale, min_clip, max_clip)
    layer_configs = {
        'HeatScore_Predicted': (lambda: (1 - dist_nw) * 15 + 35 - np.exp(-dist_ne * 5) * 15, 0.5, 38, 50),
        'HeatScore_Predicted_simulated': (lambda: (1 - dist_nw) * 15 + 34 - np.exp(-dist_ne * 5) * 15, 0.5, 38, 50),
        'HeatScore_Predicted_diff': (lambda: np.zeros((height, width)) + 1, 0.2, -10, 10),
        'LST': (lambda: (1 - dist_nw) * 15 + 33.5 - np.exp(-dist_ne * 5) * 15, 0.5, 38, 50),
        'AirTemp': (lambda: (1 - dist_nw) * 10 + 28 - np.exp(-dist_ne * 5) * 10, 0.5, 25, 45),
        'UHI_Intensity': (lambda: np.exp(-dist_ganga * 5) * 5 + 2, 0.5, -5, 10),
        'UTFVI': (lambda: np.exp(-dist_ganga * 5) * 0.5, 0.1, -1, 1),
        'NDVI': (lambda: xn * 0.5 + yn * 0.3, 0.1, -0.1, 0.8),
        'NDBI': (lambda: 1 - (xn * 0.5 + yn * 0.3), 0.1, -0.3, 0.35),
        'NDWI': (lambda: (yn - xn) * 0.5, 0.1, -0.5, 0.6),
        'MNDWI': (lambda: (yn - xn) * 0.5 + 0.1, 0.1, -0.6, 0.7),
        'Population_Density': (lambda: np.exp(-dist_ganga * 5) * 400 + 50, 20, 0, 500),
        'Building_Density': (lambda: np.exp(-dist_ganga * 5) * 80 + 10, 5, 0, 90),
        'Building_Height': (lambda: np.exp(-dist_ganga * 5) * 20 + 5, 2, 0, 30),
        'Road_Density_Proxy': (lambda: np.exp(-dist_ganga * 5) * 0.8 + 0.1, 0.1, 0, 1),
        'Anthropogenic_Heat': (lambda: np.exp(-dist_ganga * 5) * 0.9 + 0.1, 0.05, 0, 1),
        'Nighttime_Lights': (lambda: np.exp(-dist_ganga * 5) * 50 + 5, 2, 0, 63),
        'Impervious_Frac': (lambda: np.exp(-dist_ganga * 5) * 0.8 + 0.1, 0.1, 0, 1),
        'Tree_Cover_Pct': (lambda: (xn * 0.5 + yn * 0.3) * 80, 5, 0, 80),
        'Dist_Water': (lambda: np.random.uniform(0, 5000, (height, width)), 500, 0, 10000),
        'Dist_Green': (lambda: np.random.uniform(0, 2000, (height, width)), 200, 0, 5000),
        'Green_Space_Density': (lambda: (xn * 0.5 + yn * 0.3), 0.1, 0, 1),
        'Albedo': (lambda: np.random.uniform(0.1, 0.3, (height, width)), 0.05, 0.05, 0.4),
        'Humidity': (lambda: yn * 40 + 20, 5, 20, 70),
        'WindSpeed': (lambda: xn * 4 + 1, 0.5, 0, 6),
        'WindDirection': (lambda: np.random.uniform(0, 360, (height, width)), 10, 0, 360),
        'SolarRadiation': (lambda: yn * 800 + 200, 50, 0, 1000),
        'Elevation': (lambda: np.exp(-dist_ne * 5) * 300 + 50, 10, 150, 350),
        'Slope': (lambda: np.exp(-dist_ne * 5) * 10 + 1, 1, 0, 15),
        'LULC_ESA': (lambda: np.random.uniform(10, 80, (height, width)), 0, 10, 80),
        'LULC_DW': (lambda: np.random.uniform(0, 7, (height, width)), 0, 0, 7),
        'SAVI': (lambda: xn * 0.4 + yn * 0.2, 0.1, -0.1, 0.8),
        'Building_Volume': (lambda: np.exp(-dist_ganga * 5) * 400 + 50, 20, 0, 500),
        'Surface_Roughness': (lambda: np.exp(-dist_ganga * 5) * 0.8 + 0.1, 0.1, 0, 1),
        'UTCI_Approx': (lambda: (1 - dist_nw) * 10 + 30, 1, 20, 50),
        'LULC_Derived': (lambda: np.random.randint(0, 4, (height, width)), 0, 0, 3)
    }
    
    out_dir = os.path.join(project_root, '..', 'outputs', 'demo_rasters')
    os.makedirs(out_dir, exist_ok=True)
    
    profile = {
        'driver': 'GTiff',
        'height': height,
        'width': width,
        'count': 1,
        'dtype': 'float32',
        'crs': 'EPSG:4326',
        'transform': transform,
        'nodata': np.nan,
        'compress': 'deflate'
    }
    
    for name, (base_func, noise_scale, vmin, vmax) in layer_configs.items():
        arr = base_func()
        if not isinstance(arr, np.ndarray) or arr.shape != (height, width):
            arr = np.full((height, width), arr, dtype=np.float32)
        else:
            arr = arr.astype(np.float32)
            
        arr += np.random.normal(0, noise_scale, (height, width))
        arr = np.clip(arr, vmin, vmax)
        arr[mask == 0] = np.nan
        
        out_path = os.path.join(out_dir, f'{name}.tif')
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(arr.astype(np.float32), 1)
            
    print("[DEMO] All Rasters generated.")
    return {
        'raster_dir': out_dir,
        'width': width,
        'height': height,
        'bounds': {
            'north': bounds[3],
            'south': bounds[1],
            'east': bounds[2],
            'west': bounds[0]
        }
    }

if __name__ == '__main__':
    create_demo_rasters()
