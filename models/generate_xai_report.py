"""
Generate XAI reports for sample pixels across all heat stress classes.
Picks representative Low, Moderate, High, and Extreme pixels and
generates publication-quality explanations for each.
"""
import os
import sys
import json
from datetime import datetime

import pandas as pd
import numpy as np

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
from explain_prediction import HeatExplainer, HEAT_CLASSES, HEAT_CLASS_DESCRIPTIONS

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base, 'models', 'output', 'trained_model.pkl')
    data_path = os.path.join(base, 'data', 'final', 'master_dataset.csv')
    output_dir = os.path.join(base, 'outputs', 'xai_reports')
    os.makedirs(output_dir, exist_ok=True)

    print('=' * 70)
    print('  URBAN HEAT AI - EXPLAINABLE AI REPORT GENERATOR')
    print('=' * 70)

    # Load
    print('\n  Loading model and data...')
    explainer = HeatExplainer(model_path)
    df = pd.read_csv(data_path)
    print(f'  Model: {explainer.bundle["best_model_name"]}')
    print(f'  Features: {len(explainer.feature_cols)}')
    print(f'  Dataset: {len(df)} rows')

    # Engineer HeatScore to pick samples (same logic as training)
    def safe_norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn) if mx > mn else pd.Series(0.5, index=s.index)

    components = {}
    if 'LST' in df.columns: components['LST'] = safe_norm(df['LST'])
    if 'UHI_Intensity' in df.columns: components['UHI'] = safe_norm(df['UHI_Intensity'])
    if 'UTFVI' in df.columns: components['UTFVI'] = safe_norm(df['UTFVI'])
    if 'Anthropogenic_Heat' in df.columns: components['Anthro'] = safe_norm(df['Anthropogenic_Heat'])
    if 'Impervious_Frac' in df.columns: components['Imperv'] = safe_norm(df['Impervious_Frac'])

    weights = {'LST': 0.40, 'UHI': 0.25, 'UTFVI': 0.15, 'Anthro': 0.10, 'Imperv': 0.10}
    heat_raw = sum(components[k] * weights[k] for k in components if k in weights)
    df['HeatScore'] = (heat_raw * 100).clip(0, 100)

    q25, q50, q75 = df['HeatScore'].quantile([0.25, 0.5, 0.75])
    df['HeatClass'] = pd.cut(df['HeatScore'],
                              bins=[-np.inf, q25, q50, q75, np.inf],
                              labels=[0, 1, 2, 3]).astype(int)

    # Pick representative pixels: one per class, closest to class median
    print('\n  Selecting representative pixels...')
    samples = []
    for cls_id in range(4):
        subset = df[df['HeatClass'] == cls_id]
        median_score = subset['HeatScore'].median()
        idx = (subset['HeatScore'] - median_score).abs().idxmin()
        samples.append(idx)
        cls_name = HEAT_CLASSES[cls_id]
        score = df.loc[idx, 'HeatScore']
        print(f'  {cls_name:10s}: row {idx}, HeatScore={score:.1f}')

    # Also pick the absolute hottest and coolest pixels
    hottest_idx = df['HeatScore'].idxmax()
    coolest_idx = df['HeatScore'].idxmin()
    samples.extend([hottest_idx, coolest_idx])
    print(f'  {"Hottest":10s}: row {hottest_idx}, HeatScore={df.loc[hottest_idx, "HeatScore"]:.1f}')
    print(f'  {"Coolest":10s}: row {coolest_idx}, HeatScore={df.loc[coolest_idx, "HeatScore"]:.1f}')

    # Generate explanations
    all_explanations = []
    for i, idx in enumerate(samples):
        row = df.loc[idx]
        cls_id = int(row['HeatClass'])
        cls_name = HEAT_CLASSES[cls_id]

        if i < 4:
            prefix = f'{cls_name.lower()}_sample'
            label = f'{cls_name} Sample'
        elif i == 4:
            prefix = 'hottest_pixel'
            label = 'Hottest Pixel'
        else:
            prefix = 'coolest_pixel'
            label = 'Coolest Pixel'

        print(f'\n  --- Generating XAI report: {label} ---')
        expl = explainer.explain_pixel(row)
        paths = explainer.generate_full_report(expl, output_dir, prefix)

        for chart_type, path in paths.items():
            size = os.path.getsize(path) / 1024
            print(f'    {chart_type:15s}: {os.path.basename(path)} ({size:.1f} KB)')

        print(f'    Explanation: {expl.explanation_text[:120]}...')
        all_explanations.append(expl.to_dict())

    # Save combined explanations JSON
    combined_path = os.path.join(output_dir, 'all_explanations.json')
    with open(combined_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'model': explainer.bundle['best_model_name'],
            'features_used': explainer.feature_cols,
            'explanations': all_explanations,
        }, f, indent=2)
    print(f'\n  Combined JSON: {combined_path}')

    # Generate XAI documentation
    doc_path = os.path.join(output_dir, 'xai_documentation.md')
    with open(doc_path, 'w') as f:
        f.write('# Explainable AI (XAI) Documentation\n\n')
        f.write(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('---\n\n')

        f.write('## How It Works\n\n')
        f.write('When a user clicks any pixel on the map, the XAI system:\n\n')
        f.write('1. **Extracts** the pixel\'s feature values (NDVI, building density, etc.)\n')
        f.write('2. **Predicts** a Heat Score (0-100) and classifies it (Low/Moderate/High/Extreme)\n')
        f.write('3. **Computes SHAP values** for every feature using TreeExplainer\n')
        f.write('4. **Calculates contribution percentages** = |SHAP_i| / sum(|SHAP|) x 100\n')
        f.write('5. **Generates natural language** explaining WHY the location is hot/cool\n')
        f.write('6. **Recommends interventions** based on the dominant heat-causing features\n\n')

        f.write('## SHAP (SHapley Additive exPlanations)\n\n')
        f.write('SHAP values decompose each prediction into additive feature contributions:\n\n')
        f.write('```\n')
        f.write('HeatScore = BaseValue + SHAP(UHI) + SHAP(Building) + SHAP(NDBI) + ...\n')
        f.write('```\n\n')
        f.write('- **Positive SHAP** = feature INCREASES heat at this location\n')
        f.write('- **Negative SHAP** = feature DECREASES heat at this location\n')
        f.write('- **Magnitude** = how strongly the feature influences the prediction\n\n')
        f.write('Reference: Lundberg & Lee (2017), NeurIPS.\n\n')

        f.write('## Visualization Types\n\n')
        f.write('| Chart | Purpose |\n')
        f.write('|-------|--------|\n')
        f.write('| **Waterfall** | Shows each feature\'s SHAP contribution, ordered by impact |\n')
        f.write('| **Contribution Bars** | Horizontal bar chart of contribution percentages |\n')
        f.write('| **Pie Chart** | Proportional breakdown of feature influence |\n')
        f.write('| **Decision Summary** | 4-panel infographic: gauge + bars + table + explanation |\n\n')

        f.write('## Heat Stress Classes\n\n')
        f.write('| Class | Score Range | Description |\n')
        f.write('|-------|------------|-------------|\n')
        f.write(f'| Low | < {q25:.1f} | {HEAT_CLASS_DESCRIPTIONS["Low"]} |\n')
        f.write(f'| Moderate | {q25:.1f} - {q50:.1f} | {HEAT_CLASS_DESCRIPTIONS["Moderate"]} |\n')
        f.write(f'| High | {q50:.1f} - {q75:.1f} | {HEAT_CLASS_DESCRIPTIONS["High"]} |\n')
        f.write(f'| Extreme | >= {q75:.1f} | {HEAT_CLASS_DESCRIPTIONS["Extreme"]} |\n\n')

        f.write('## Sample Explanations\n\n')
        for expl_dict in all_explanations:
            cls = expl_dict['heat_class']
            score = expl_dict['heat_score']
            f.write(f'### {cls} Heat Stress (Score: {score:.1f})\n\n')
            f.write(f'Location: ({expl_dict["latitude"]:.4f}, {expl_dict["longitude"]:.4f})\n\n')

            f.write('**Top Contributing Factors:**\n\n')
            for cause in expl_dict.get('top_causes', [])[:5]:
                f.write(f'- {cause}\n')
            f.write('\n')

            f.write('**Feature Contributions:**\n\n')
            f.write('| Feature | Contribution % |\n')
            f.write('|---------|---------------|\n')
            sorted_c = sorted(expl_dict.get('contributions', {}).items(),
                              key=lambda x: x[1], reverse=True)
            for feat, pct in sorted_c[:10]:
                f.write(f'| {feat} | {pct:.1f}% |\n')
            f.write('\n')

            if expl_dict.get('recommendation'):
                f.write('**Recommendations:**\n\n')
                f.write(expl_dict['recommendation'] + '\n\n')

            f.write('---\n\n')

        f.write('## Usage in Code\n\n')
        f.write('```python\n')
        f.write('from utils.explain_prediction import HeatExplainer\n\n')
        f.write('explainer = HeatExplainer("models/output/trained_model.pkl")\n\n')
        f.write('# For any pixel row from master_dataset.csv:\n')
        f.write('explanation = explainer.explain_pixel(pixel_row)\n\n')
        f.write('# Access results:\n')
        f.write('print(explanation.heat_score)        # 0-100\n')
        f.write('print(explanation.heat_class)         # "Low"/"Moderate"/"High"/"Extreme"\n')
        f.write('print(explanation.contributions_pct)  # {feature: %}\n')
        f.write('print(explanation.top_causes)          # Natural language list\n')
        f.write('print(explanation.explanation_text)    # Full paragraph\n')
        f.write('print(explanation.recommendation)     # Intervention suggestions\n\n')
        f.write('# Generate charts:\n')
        f.write('explainer.generate_full_report(explanation, "output_dir/", "pixel_001")\n')
        f.write('```\n')

    print(f'  Documentation: {doc_path}')

    # Summary
    n_charts = len(samples) * 4  # 4 charts per pixel
    print(f'\n' + '=' * 70)
    print(f'  XAI REPORT GENERATION COMPLETE')
    print(f'=' * 70)
    print(f'  Pixels explained: {len(samples)}')
    print(f'  Charts generated: {n_charts}')
    print(f'  Output directory: {output_dir}')
    print()


if __name__ == '__main__':
    main()
