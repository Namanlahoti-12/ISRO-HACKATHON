"""
Urban Cooling Optimization Engine
==================================
Physics-informed intervention planning system for Urban Heat Island mitigation.

Modules:
    intervention_library  — Catalog of cooling interventions with physics parameters
    hotspot_detector      — Detect and classify UHI hotspots from trained model
    feature_modifier      — Physics-based feature modification engine
    optimizer             — NSGA-II multi-objective optimization
    cooling_engine        — Main orchestrator
    report_generator      — Output CSV/JSON reports
    map_generator         — Spatial heatmap visualizations
"""

__version__ = '1.0.0'
__author__ = 'UrbanHeatAI Team'
