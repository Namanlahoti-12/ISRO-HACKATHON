"""Generate a realistic mock CSV matching the updated GEE pipeline (with SAVI)."""
import csv
import random
import os

random.seed(42)

COLUMNS = [
    'PixelID', 'Latitude', 'Longitude', 'Timestamp',
    'LST',
    'NDVI', 'NDBI', 'NDWI', 'MNDWI', 'SAVI', 'Albedo',
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

ESA_CLASSES = [10, 20, 30, 40, 50, 60, 80]
DW_CLASSES = [0, 1, 2, 3, 4, 5, 6, 7]

output_dir = os.path.join('UrbanHeatAI', 'data', 'raw')
output_path = os.path.join(output_dir, 'Delhi_UHI_MasterDataset.csv')
os.makedirs(output_dir, exist_ok=True)

with open(output_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()

    for i in range(2000):
        lulc = random.choice(ESA_CLASSES)
        is_urban = (lulc == 50)
        is_water = (lulc == 80)
        is_green = (lulc in [10, 20, 30])

        lat = 28.6139 + random.uniform(-0.15, 0.15)
        lon = 77.2090 + random.uniform(-0.15, 0.15)

        base_lst = 38 + random.gauss(0, 3)
        if is_urban:
            base_lst += random.uniform(3, 8)
        elif is_green:
            base_lst -= random.uniform(2, 6)
        elif is_water:
            base_lst -= random.uniform(5, 10)

        ndvi = random.uniform(0.5, 0.8) if is_green else (
            random.uniform(-0.1, 0.15) if is_urban else random.uniform(0.1, 0.4))
        ndbi = random.uniform(0.1, 0.35) if is_urban else random.uniform(-0.3, 0.05)
        ndwi = random.uniform(0.1, 0.6) if is_water else random.uniform(-0.5, 0.0)
        savi = ndvi * 1.5 / 1.5  # SAVI with L=0.5
        
        sr = random.uniform(180, 320)

        row = {
            'PixelID': i,
            'Latitude': round(lat, 6),
            'Longitude': round(lon, 6),
            'Timestamp': '2024-03-01_to_2024-06-30',
            'LST': round(base_lst, 2),
            'NDVI': round(ndvi, 4),
            'NDBI': round(ndbi, 4),
            'NDWI': round(ndwi, 4),
            'MNDWI': round(ndwi + random.uniform(-0.1, 0.1), 4),
            'SAVI': round(savi, 4),
            'Albedo': round(random.uniform(0.08, 0.35), 4),
            'LULC_ESA': lulc,
            'LULC_DW': random.choice(DW_CLASSES),
            'Impervious_Frac': 1 if is_urban else 0,
            'Tree_Cover_Pct': round(random.uniform(40, 80) if is_green else random.uniform(0, 15), 1),
            'AirTemp': round(35 + random.gauss(0, 2), 2),
            'Humidity': round(random.uniform(25, 65), 2),
            'WindSpeed': round(random.uniform(1, 5), 2),
            'WindDirection': round(random.uniform(0, 360), 1),
            'SolarRadiation': round(sr, 2),
            'Pressure': round(random.uniform(990, 1015), 2),
            'Rainfall': round(random.uniform(0, 150), 2),
            'Elevation': round(random.uniform(200, 280), 1),
            'Slope': round(random.uniform(0, 5), 2),
            'Aspect': round(random.uniform(0, 360), 1),
            'Building_Density': round(random.uniform(30, 90) if is_urban else random.uniform(0, 10), 2),
            'Building_Height': round(random.uniform(8, 30) if is_urban else random.uniform(0, 5), 2),
            'Building_Volume': 0,
            'Nighttime_Lights': round(random.uniform(20, 60) if is_urban else random.uniform(0, 10), 2),
            'Population_Density': round(random.uniform(200, 2000) if is_urban else random.uniform(0, 100), 1),
            'Dist_Water': round(random.uniform(0, 5000), 1),
            'Dist_Green': round(random.uniform(0, 100) if is_green else random.uniform(200, 3000), 1),
            'Green_Space_Density': round(ndvi * random.uniform(0.5, 1.0) if ndvi > 0.3 else random.uniform(0, 0.15), 4),
            'Surface_Roughness': round(random.uniform(0.5, 8), 2),
            'Anthropogenic_Heat': round(random.uniform(0.1, 0.8) if is_urban else random.uniform(0, 0.1), 4),
            'Road_Density_Proxy': round(random.uniform(0, 0.5) if is_urban else random.uniform(-0.1, 0.1), 4),
            'UHI_Intensity': round(base_lst - 36, 2),
            'UTFVI': round((base_lst - 38) / 38, 4),
            'QualityScore': random.randint(1, 18),
        }
        row['Building_Volume'] = round(row['Building_Density'] * row['Building_Height'], 2)
        
        # Add some NaN values randomly for realism (2% sparsity)
        if random.random() < 0.02:
            row['Building_Height'] = ''
        if random.random() < 0.01:
            row['Nighttime_Lights'] = ''
        
        writer.writerow(row)

print(f'Generated {output_path} with 2000 rows x {len(COLUMNS)} columns')
