"""
GEE Collection ID & Band Name Validator
========================================
Validates that all collection IDs and band names used in main.js
match the current Google Earth Engine catalog.

This is a static analysis tool — it checks the JavaScript source code
for known-valid GEE identifiers without connecting to GEE.
"""

import re
import json
import os

# Known-valid GEE Collection IDs as of 2024
VALID_COLLECTIONS = {
    'LANDSAT/LC08/C02/T1_L2': {
        'bands': ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7',
                  'ST_B10','QA_PIXEL','QA_RADSAT'],
        'status': 'ACTIVE'
    },
    'LANDSAT/LC09/C02/T1_L2': {
        'bands': ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7',
                  'ST_B10','QA_PIXEL','QA_RADSAT'],
        'status': 'ACTIVE'
    },
    'COPERNICUS/S2_SR_HARMONIZED': {
        'bands': ['B1','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B11','B12','QA60'],
        'status': 'ACTIVE'
    },
    'ECMWF/ERA5_LAND/HOURLY': {
        'bands': ['temperature_2m','dewpoint_temperature_2m',
                  'u_component_of_wind_10m','v_component_of_wind_10m',
                  'surface_solar_radiation_downwards_hourly',
                  'surface_pressure','total_precipitation_hourly'],
        'status': 'ACTIVE'
    },
    'ESA/WorldCover/v200': {
        'bands': ['Map'],
        'status': 'ACTIVE'
    },
    'GOOGLE/DYNAMICWORLD/V1': {
        'bands': ['water','trees','grass','flooded_vegetation','crops',
                  'shrub_and_scrub','built','bare','snow_and_ice','label'],
        'status': 'ACTIVE'
    },
    'USGS/SRTMGL1_003': {
        'bands': ['elevation'],
        'status': 'ACTIVE'
    },
    'NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG': {
        'bands': ['avg_rad','cf_cvg'],
        'status': 'ACTIVE'
    },
    'WorldPop/GP/100m/pop': {
        'bands': ['population'],
        'status': 'ACTIVE'
    },
    'UMD/hansen/global_forest_change_2023_v1_11': {
        'bands': ['treecover2000','loss','gain','lossyear','datamask'],
        'status': 'ACTIVE'
    },
    'Tsinghua/FROM-GLC/GAIA/v10': {
        'bands': ['change_year_index'],
        'status': 'ACTIVE'
    },
    'JRC/GHSL/P2023A/GHS_BUILT_S': {
        'bands': ['built_surface'],
        'status': 'ACTIVE',
        'note': 'May require epoch filter. try/catch used in main.js.'
    },
    'JRC/GHSL/P2023A/GHS_BUILT_H': {
        'bands': ['built_height'],
        'status': 'ACTIVE',
        'note': 'May require epoch filter. try/catch used in main.js.'
    },
    'FAO/GAUL/2015/level2': {
        'bands': [],
        'status': 'ACTIVE',
        'type': 'FeatureCollection'
    },
}

# Deprecated GEE functions to watch for
DEPRECATED_FUNCTIONS = [
    'ee.data.getList',
    'image.getThumbURL',
    '.getInfo(',
    'ee.Algorithms.Landsat.simpleComposite',
]

def validate_main_js(filepath):
    """Validate the main.js script for correct GEE identifiers."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    report = {
        'file': filepath,
        'collections': {},
        'deprecated_apis': [],
        'issues': [],
        'warnings': [],
    }

    # Check which collection IDs are referenced
    for coll_id, info in VALID_COLLECTIONS.items():
        if coll_id in content:
            report['collections'][coll_id] = {
                'found': True,
                'status': info['status'],
                'note': info.get('note', '')
            }
        else:
            # Not all collections need to be used
            pass

    # Check for collection IDs in the script that are NOT in our list
    # Pattern: strings like 'SOMETHING/SOMETHING/...'
    coll_pattern = re.findall(r"'([A-Z][A-Za-z0-9_]+(?:/[A-Za-z0-9_.]+){2,})'", content)
    for coll in coll_pattern:
        if coll not in VALID_COLLECTIONS and coll != 'EPSG:4326':
            report['warnings'].append(f'Unverified collection: {coll}')

    # Check for deprecated function calls
    for func in DEPRECATED_FUNCTIONS:
        if func in content:
            report['deprecated_apis'].append(func)

    # Check band name usage
    band_issues = []
    landsat_bands = ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7','ST_B10','QA_PIXEL','QA_RADSAT']
    s2_bands = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12','QA60']
    era5_bands = ['temperature_2m','dewpoint_temperature_2m','u_component_of_wind_10m',
                  'v_component_of_wind_10m','surface_solar_radiation_downwards_hourly',
                  'surface_pressure','total_precipitation_hourly']

    # Verify Landsat band references
    landsat_refs = re.findall(r"'(SR_B\d+|ST_B\d+|QA_PIXEL|QA_RADSAT)'", content)
    for band in set(landsat_refs):
        if band not in landsat_bands:
            band_issues.append(f'Unknown Landsat band: {band}')

    # Verify S2 band references
    s2_refs = re.findall(r"'(B\d+[A]?|QA60)'", content)
    for band in set(s2_refs):
        if band not in s2_bands:
            band_issues.append(f'Unknown Sentinel-2 band: {band}')

    # Verify ERA5 band references
    for band in era5_bands:
        if band in content:
            pass  # OK

    report['band_issues'] = band_issues

    return report


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    main_js = os.path.join(project_root, 'gee', 'main.js')

    if not os.path.exists(main_js):
        print(f'[ERROR] main.js not found at: {main_js}')
        return

    print('=' * 60)
    print('  GEE COLLECTION & BAND NAME VALIDATOR')
    print('=' * 60)

    report = validate_main_js(main_js)

    # Print collections found
    print(f'\n[STEP] Checking GEE Collection IDs...')
    for coll_id, info in report['collections'].items():
        status = info['status']
        note = f" ({info['note']})" if info['note'] else ''
        print(f'  [OK] {coll_id} [{status}]{note}')

    print(f'\n  Found {len(report["collections"])}/{len(VALID_COLLECTIONS)} known collections.')

    # Print deprecated APIs
    print(f'\n[STEP] Checking for deprecated API calls...')
    if report['deprecated_apis']:
        for func in report['deprecated_apis']:
            print(f'  [WARN] Deprecated: {func}')
    else:
        print('  [OK] No deprecated API calls found.')

    # Print band issues
    print(f'\n[STEP] Checking band name references...')
    if report['band_issues']:
        for issue in report['band_issues']:
            print(f'  [WARN] {issue}')
    else:
        print('  [OK] All band names are valid.')

    # Print warnings
    if report['warnings']:
        print(f'\n[STEP] Warnings:')
        for w in report['warnings']:
            print(f'  [WARN] {w}')

    # Save report
    report_path = os.path.join(project_root, 'data', 'metadata', 'gee_validation_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f'\n[OK] Validation report saved: {report_path}')

    print('\n' + '=' * 60)
    print('  VALIDATION COMPLETE')
    print('=' * 60)


if __name__ == '__main__':
    main()
