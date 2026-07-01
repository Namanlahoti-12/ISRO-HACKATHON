"""
Intervention Library — Physics-Informed Urban Cooling Interventions
=====================================================================
Complete catalog of 33 cooling interventions across 4 categories (Green/White/Blue/Grey),
each mapped to specific dataset features with scientifically-grounded modification
parameters derived from peer-reviewed urban climate literature.

Literature Sources:
    - Oke et al. (2017) "Urban Climates" Cambridge University Press
    - Akbari et al. (2001) "Cool surfaces and shade trees to reduce energy use"
    - Bowler et al. (2010) "Urban greening to cool towns and cities"
    - Santamouris (2014) "Cooling the cities: a review of reflective and green roof"
    - Gunawardena et al. (2017) "Utilising green and bluespace to mitigate UHI"
    - Stewart & Oke (2012) "Local Climate Zones for Urban Temperature Studies"
"""

import json
import os
from typing import Dict, List, Optional


# =============================================================================
# INTERVENTION DATA STRUCTURE
# =============================================================================

INTERVENTION_LIBRARY = {

    # =========================================================================
    # GREEN INTERVENTIONS — Vegetation-based cooling
    # Mechanism: Evapotranspiration + Shading + Albedo modification
    # =========================================================================

    "street_trees": {
        "id": "street_trees",
        "name": "Street Trees",
        "category": "green",
        "description": "Planting shade trees along streets and sidewalks. "
                       "Trees provide evapotranspiration cooling (latent heat flux) "
                       "and reduce solar radiation reaching surfaces by 60-90%.",
        "cooling_potential_celsius": {"min": 1.0, "max": 3.5, "typical": 2.0},
        "cost_per_unit": {"value": 500, "unit": "USD/tree", "annual_maintenance": 75},
        "implementation_time_months": {"min": 3, "max": 12},
        "lifespan_years": 30,
        "effectiveness_lag_years": 3,
        "co_benefits": [
            "Air quality improvement",
            "Carbon sequestration",
            "Stormwater management",
            "Aesthetic value",
            "Mental health benefits",
            "Biodiversity support"
        ],
        "constraints": [
            "Requires adequate soil depth",
            "Underground utility clearance",
            "Minimum 2m sidewalk width",
            "Species must tolerate urban pollution"
        ],
        "applicable_lulc": [50, 30, 40],  # Built-up, Grassland, Cropland (ESA codes)
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.15, "range": [0.10, 0.25]},
            "Tree_Cover_Pct":    {"delta_mode": "add", "value": 15.0, "range": [8.0, 25.0]},
            "NDBI":              {"delta_mode": "add", "value": -0.05, "range": [-0.08, -0.02]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.10, "range": [0.05, 0.20]},
            "Albedo":            {"delta_mode": "add", "value": -0.02, "range": [-0.04, -0.01]},
            "Surface_Roughness": {"delta_mode": "add", "value": 0.15, "range": [0.08, 0.25]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.92, "range": [0.88, 0.96]},
            "Dist_Green":        {"delta_mode": "multiply", "value": 0.60, "range": [0.40, 0.80]},
        },
        "physics_model": {
            "mechanism": "evapotranspiration + shading",
            "latent_heat_flux_w_m2": 80,    # W/m² per mature tree canopy
            "shade_fraction": 0.70,          # Fraction of ground shaded
            "transpiration_rate_l_day": 400,  # Liters per day per mature tree
        },
        "feasibility_score": 0.85,
        "scalability": "high",
        "indian_suitability": "high",
        "recommended_species_india": [
            "Azadirachta indica (Neem)",
            "Ficus religiosa (Peepal)",
            "Delonix regia (Gulmohar)",
            "Pongamia pinnata (Karanj)",
            "Alstonia scholaris (Saptaparni)"
        ],
    },

    "urban_forests": {
        "id": "urban_forests",
        "name": "Urban Forests / Miyawaki Forests",
        "category": "green",
        "description": "Dense native plantations using the Miyawaki method. "
                       "Creates multi-layered canopy cover achieving 2-5°C cooling "
                       "through intensive evapotranspiration and wind channeling.",
        "cooling_potential_celsius": {"min": 2.0, "max": 5.0, "typical": 3.0},
        "cost_per_unit": {"value": 15000, "unit": "USD/hectare", "annual_maintenance": 2000},
        "implementation_time_months": {"min": 2, "max": 6},
        "lifespan_years": 50,
        "effectiveness_lag_years": 2,
        "co_benefits": [
            "Major carbon sequestration",
            "Biodiversity hotspot",
            "Flood mitigation",
            "Noise reduction",
            "Recreational space"
        ],
        "constraints": [
            "Requires minimum 100 sqm contiguous area",
            "Heavy initial planting density (3 trees/sqm)",
            "Regular watering for first 2 years"
        ],
        "applicable_lulc": [60, 30, 40, 50],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.30, "range": [0.20, 0.45]},
            "Tree_Cover_Pct":    {"delta_mode": "add", "value": 40.0, "range": [25.0, 60.0]},
            "NDBI":              {"delta_mode": "add", "value": -0.15, "range": [-0.25, -0.08]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.20, "range": [-0.35, -0.10]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.30, "range": [0.20, 0.45]},
            "Albedo":            {"delta_mode": "add", "value": -0.03, "range": [-0.05, -0.01]},
            "Surface_Roughness": {"delta_mode": "add", "value": 0.30, "range": [0.20, 0.45]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.80, "range": [0.70, 0.90]},
            "Dist_Green":        {"delta_mode": "multiply", "value": 0.20, "range": [0.10, 0.40]},
        },
        "physics_model": {
            "mechanism": "dense evapotranspiration + wind channeling",
            "latent_heat_flux_w_m2": 200,
            "shade_fraction": 0.95,
            "transpiration_rate_l_day": 2000,
        },
        "feasibility_score": 0.70,
        "scalability": "medium",
        "indian_suitability": "high",
    },

    "pocket_parks": {
        "id": "pocket_parks",
        "name": "Pocket Parks",
        "category": "green",
        "description": "Small green spaces (200-2000 sqm) distributed throughout "
                       "dense urban fabric. Provide localized cooling within 50-100m "
                       "radius through evapotranspiration and reduced surface heating.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.5},
        "cost_per_unit": {"value": 25000, "unit": "USD/park", "annual_maintenance": 3000},
        "implementation_time_months": {"min": 3, "max": 9},
        "lifespan_years": 25,
        "effectiveness_lag_years": 1,
        "co_benefits": [
            "Community gathering space",
            "Children's play area",
            "Stormwater infiltration",
            "Property value increase"
        ],
        "constraints": [
            "Requires available urban land",
            "Minimum 200 sqm area",
            "Access to irrigation water"
        ],
        "applicable_lulc": [50, 60],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.12, "range": [0.06, 0.20]},
            "Tree_Cover_Pct":    {"delta_mode": "add", "value": 10.0, "range": [5.0, 20.0]},
            "NDBI":              {"delta_mode": "add", "value": -0.06, "range": [-0.10, -0.03]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.08, "range": [-0.15, -0.04]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.15, "range": [0.08, 0.25]},
            "Dist_Green":        {"delta_mode": "multiply", "value": 0.40, "range": [0.25, 0.60]},
        },
        "physics_model": {
            "mechanism": "evapotranspiration + surface replacement",
            "latent_heat_flux_w_m2": 60,
            "shade_fraction": 0.40,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "green_roofs": {
        "id": "green_roofs",
        "name": "Green Roofs",
        "category": "green",
        "description": "Vegetation layers installed on rooftops. Extensive (sedum, 5-15cm "
                       "substrate) or intensive (shrubs/trees, 15-100cm substrate). "
                       "Cooling via evapotranspiration + insulation + albedo shift.",
        "cooling_potential_celsius": {"min": 0.5, "max": 3.0, "typical": 1.5},
        "cost_per_unit": {"value": 120, "unit": "USD/sqm", "annual_maintenance": 8},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0.5,
        "co_benefits": [
            "Building insulation (20-30% energy savings)",
            "Stormwater retention (50-90%)",
            "Extended roof lifespan",
            "Urban agriculture potential",
            "Noise insulation"
        ],
        "constraints": [
            "Structural load capacity (60-300 kg/sqm)",
            "Waterproof membrane required",
            "Irrigation system for intensive type",
            "Not suitable for sloped roofs >30°"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.10, "range": [0.05, 0.20]},
            "NDBI":              {"delta_mode": "add", "value": -0.08, "range": [-0.15, -0.04]},
            "Albedo":            {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.05, "range": [-0.10, -0.02]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.90, "range": [0.85, 0.95]},
        },
        "physics_model": {
            "mechanism": "evapotranspiration + insulation",
            "latent_heat_flux_w_m2": 45,
            "thermal_resistance_m2k_w": 1.2,
        },
        "feasibility_score": 0.75,
        "scalability": "high",
        "indian_suitability": "medium",
    },

    "green_walls": {
        "id": "green_walls",
        "name": "Green Walls / Living Walls",
        "category": "green",
        "description": "Vertical vegetation systems on building facades. "
                       "Reduce wall surface temperature by 5-15°C through shading "
                       "and evapotranspiration. Reduce indoor cooling load by 20-40%.",
        "cooling_potential_celsius": {"min": 0.3, "max": 1.5, "typical": 0.8},
        "cost_per_unit": {"value": 200, "unit": "USD/sqm", "annual_maintenance": 15},
        "implementation_time_months": {"min": 1, "max": 3},
        "lifespan_years": 15,
        "effectiveness_lag_years": 0.5,
        "co_benefits": [
            "Building cooling load reduction",
            "Air quality at pedestrian level",
            "Aesthetic improvement",
            "Noise reduction"
        ],
        "constraints": [
            "Structural assessment required",
            "Irrigation system needed",
            "Regular maintenance (pruning)",
            "Building owner consent"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
            "NDBI":              {"delta_mode": "add", "value": -0.03, "range": [-0.06, -0.01]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.03, "range": [0.01, 0.06]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.93, "range": [0.88, 0.97]},
        },
        "physics_model": {
            "mechanism": "shading + evapotranspiration on vertical surfaces",
            "latent_heat_flux_w_m2": 25,
            "wall_temp_reduction_celsius": 10,
        },
        "feasibility_score": 0.65,
        "scalability": "medium",
        "indian_suitability": "medium",
    },

    "vertical_gardens": {
        "id": "vertical_gardens",
        "name": "Vertical Gardens",
        "category": "green",
        "description": "Modular planting systems on building exteriors "
                       "and freestanding structures. Combines aesthetic greening "
                       "with localized evaporative cooling.",
        "cooling_potential_celsius": {"min": 0.2, "max": 1.0, "typical": 0.5},
        "cost_per_unit": {"value": 180, "unit": "USD/sqm", "annual_maintenance": 12},
        "implementation_time_months": {"min": 1, "max": 2},
        "lifespan_years": 10,
        "effectiveness_lag_years": 0.3,
        "co_benefits": [
            "Urban beautification",
            "Food production potential",
            "Educational value"
        ],
        "constraints": [
            "Requires regular irrigation",
            "Structural support needed",
            "Plant replacement cycle"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.04, "range": [0.02, 0.08]},
            "NDBI":              {"delta_mode": "add", "value": -0.02, "range": [-0.04, -0.01]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.02, "range": [0.01, 0.04]},
        },
        "physics_model": {
            "mechanism": "localized evapotranspiration",
            "latent_heat_flux_w_m2": 15,
        },
        "feasibility_score": 0.70,
        "scalability": "medium",
        "indian_suitability": "medium",
    },

    "bioswales": {
        "id": "bioswales",
        "name": "Bioswales",
        "category": "green",
        "description": "Vegetated drainage channels that filter stormwater runoff. "
                       "Replace impervious gutters with living systems that provide "
                       "evaporative cooling and groundwater recharge.",
        "cooling_potential_celsius": {"min": 0.3, "max": 1.5, "typical": 0.8},
        "cost_per_unit": {"value": 60, "unit": "USD/linear meter", "annual_maintenance": 5},
        "implementation_time_months": {"min": 2, "max": 6},
        "lifespan_years": 20,
        "effectiveness_lag_years": 1,
        "co_benefits": [
            "Stormwater management",
            "Water quality improvement",
            "Flood risk reduction",
            "Groundwater recharge"
        ],
        "constraints": [
            "Requires adequate slope (1-5%)",
            "Soil permeability assessment",
            "Not suitable in high water table areas"
        ],
        "applicable_lulc": [50, 30],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.06, "range": [0.03, 0.10]},
            "MNDWI":             {"delta_mode": "add", "value": 0.03, "range": [0.01, 0.06]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.04, "range": [-0.08, -0.02]},
            "NDBI":              {"delta_mode": "add", "value": -0.03, "range": [-0.05, -0.01]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.04, "range": [0.02, 0.08]},
        },
        "physics_model": {
            "mechanism": "evapotranspiration + surface replacement",
            "latent_heat_flux_w_m2": 30,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "urban_agriculture": {
        "id": "urban_agriculture",
        "name": "Urban Agriculture",
        "category": "green",
        "description": "Community gardens, rooftop farms, and peri-urban agriculture. "
                       "Replaces impervious surfaces with productive vegetation providing "
                       "evapotranspiration cooling and food security benefits.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 8000, "unit": "USD/hectare", "annual_maintenance": 1500},
        "implementation_time_months": {"min": 2, "max": 6},
        "lifespan_years": 15,
        "effectiveness_lag_years": 0.5,
        "co_benefits": [
            "Food security",
            "Community engagement",
            "Income generation",
            "Educational value"
        ],
        "constraints": [
            "Soil contamination testing required",
            "Water supply needed",
            "Community management structure"
        ],
        "applicable_lulc": [50, 60, 30],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.12, "range": [0.06, 0.20]},
            "NDBI":              {"delta_mode": "add", "value": -0.06, "range": [-0.10, -0.03]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.10, "range": [-0.18, -0.05]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.10, "range": [0.05, 0.18]},
        },
        "physics_model": {
            "mechanism": "evapotranspiration + surface replacement",
            "latent_heat_flux_w_m2": 55,
        },
        "feasibility_score": 0.75,
        "scalability": "medium",
        "indian_suitability": "high",
    },

    # =========================================================================
    # WHITE INTERVENTIONS — Reflective/Albedo-based cooling
    # Mechanism: Increase surface reflectivity → reduce absorbed solar radiation
    # =========================================================================

    "cool_roofs": {
        "id": "cool_roofs",
        "name": "Cool Roofs",
        "category": "white",
        "description": "High-reflectivity roofing materials (white membranes, tiles, "
                       "or coatings) that reflect 60-80% of solar radiation. One of the "
                       "most cost-effective UHI interventions per Akbari et al. (2001).",
        "cooling_potential_celsius": {"min": 0.5, "max": 3.0, "typical": 1.5},
        "cost_per_unit": {"value": 15, "unit": "USD/sqm", "annual_maintenance": 1},
        "implementation_time_months": {"min": 0.5, "max": 2},
        "lifespan_years": 15,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "20-40% AC energy savings",
            "Extended roof membrane life",
            "Peak demand reduction",
            "Quick implementation"
        ],
        "constraints": [
            "May increase heating costs in winter (negligible in tropical India)",
            "Glare issues for neighbors/aircraft",
            "Regular cleaning needed to maintain reflectivity",
            "Not suitable for rooftop solar panels (reduces PV output by 5%)"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Albedo":            {"delta_mode": "set_max", "value": 0.70, "range": [0.55, 0.80]},
            "NDBI":              {"delta_mode": "add", "value": -0.03, "range": [-0.06, -0.01]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.80, "range": [0.70, 0.88]},
            "SolarRadiation":    {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
        },
        "physics_model": {
            "mechanism": "increased shortwave reflectivity",
            "albedo_before": 0.15,
            "albedo_after": 0.70,
            "net_radiation_reduction_w_m2": 150,
        },
        "feasibility_score": 0.95,
        "scalability": "very_high",
        "indian_suitability": "very_high",
    },

    "reflective_roof_coatings": {
        "id": "reflective_roof_coatings",
        "name": "Reflective Roof Coatings",
        "category": "white",
        "description": "Spray-applied or painted reflective coatings for existing roofs. "
                       "Simpler than full cool roof replacement. White lime wash (chuna) "
                       "is a traditional Indian approach.",
        "cooling_potential_celsius": {"min": 0.3, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 5, "unit": "USD/sqm", "annual_maintenance": 2},
        "implementation_time_months": {"min": 0.25, "max": 1},
        "lifespan_years": 5,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Very low cost",
            "Community-applied (unskilled labor)",
            "Quick implementation",
            "Traditional practice in India"
        ],
        "constraints": [
            "Shorter lifespan than membrane cool roofs",
            "Needs reapplication every 3-5 years",
            "Performance degrades with dust/pollution"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Albedo":            {"delta_mode": "set_max", "value": 0.60, "range": [0.45, 0.70]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.85, "range": [0.78, 0.92]},
        },
        "physics_model": {
            "mechanism": "increased shortwave reflectivity (coating)",
            "albedo_before": 0.15,
            "albedo_after": 0.60,
            "net_radiation_reduction_w_m2": 100,
        },
        "feasibility_score": 0.95,
        "scalability": "very_high",
        "indian_suitability": "very_high",
    },

    "cool_pavements": {
        "id": "cool_pavements",
        "name": "Cool Pavements",
        "category": "white",
        "description": "High-albedo road and pavement surfaces using light-colored "
                       "aggregate, reflective coatings, or porous asphalt. Reduces "
                       "pavement surface temperature by 5-15°C.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.2},
        "cost_per_unit": {"value": 25, "unit": "USD/sqm", "annual_maintenance": 2},
        "implementation_time_months": {"min": 1, "max": 6},
        "lifespan_years": 10,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Reduced tire wear",
            "Better night visibility",
            "Lower street-level air temperature",
            "Reduced stormwater runoff"
        ],
        "constraints": [
            "Higher initial cost than conventional pavement",
            "Skid resistance must be maintained",
            "Aesthetics may not suit all areas",
            "Durability under heavy traffic"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Albedo":            {"delta_mode": "add", "value": 0.15, "range": [0.10, 0.25]},
            "NDBI":              {"delta_mode": "add", "value": -0.02, "range": [-0.05, -0.01]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.02, "range": [-0.05, 0.0]},
        },
        "physics_model": {
            "mechanism": "increased pavement reflectivity",
            "albedo_before": 0.10,
            "albedo_after": 0.35,
            "surface_temp_reduction_celsius": 10,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "reflective_concrete": {
        "id": "reflective_concrete",
        "name": "Reflective Concrete",
        "category": "white",
        "description": "White or light-colored concrete for sidewalks, plazas, "
                       "and parking areas. Uses white cement or titanium dioxide additives "
                       "for enhanced reflectivity.",
        "cooling_potential_celsius": {"min": 0.3, "max": 1.5, "typical": 0.8},
        "cost_per_unit": {"value": 35, "unit": "USD/sqm", "annual_maintenance": 1},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Durable surface",
            "Reduced lighting needs (reflective)",
            "Lower maintenance than asphalt"
        ],
        "constraints": [
            "Higher cost than regular concrete",
            "Glare potential",
            "Staining in high-traffic areas"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Albedo":            {"delta_mode": "add", "value": 0.12, "range": [0.08, 0.20]},
            "NDBI":              {"delta_mode": "add", "value": -0.01, "range": [-0.03, 0.0]},
        },
        "physics_model": {
            "mechanism": "increased concrete reflectivity",
            "albedo_before": 0.25,
            "albedo_after": 0.45,
        },
        "feasibility_score": 0.75,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "high_albedo_materials": {
        "id": "high_albedo_materials",
        "name": "High Albedo Materials",
        "category": "white",
        "description": "General category for high-reflectivity building and surface "
                       "materials including white paint, light-colored cladding, and "
                       "reflective wall coatings.",
        "cooling_potential_celsius": {"min": 0.2, "max": 1.5, "typical": 0.7},
        "cost_per_unit": {"value": 10, "unit": "USD/sqm", "annual_maintenance": 1},
        "implementation_time_months": {"min": 0.5, "max": 3},
        "lifespan_years": 10,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Reduced cooling energy",
            "Improved visual comfort",
            "Low-tech solution"
        ],
        "constraints": [
            "Aesthetics may limit adoption",
            "Maintenance to prevent soiling"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Albedo":            {"delta_mode": "add", "value": 0.10, "range": [0.05, 0.18]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.90, "range": [0.85, 0.95]},
        },
        "physics_model": {
            "mechanism": "general albedo enhancement",
            "albedo_increase": 0.10,
        },
        "feasibility_score": 0.90,
        "scalability": "very_high",
        "indian_suitability": "very_high",
    },

    # =========================================================================
    # BLUE INTERVENTIONS — Water-based cooling
    # Mechanism: Evaporative cooling + thermal mass + humidity
    # =========================================================================

    "lake_restoration": {
        "id": "lake_restoration",
        "name": "Lake Restoration",
        "category": "blue",
        "description": "Restoration and desilting of existing urban lakes. Indian cities "
                       "have lost 30-70% of their historical water bodies. Restoration "
                       "provides 2-6°C cooling within 500m radius.",
        "cooling_potential_celsius": {"min": 2.0, "max": 6.0, "typical": 3.5},
        "cost_per_unit": {"value": 500000, "unit": "USD/lake", "annual_maintenance": 25000},
        "implementation_time_months": {"min": 12, "max": 36},
        "lifespan_years": 50,
        "effectiveness_lag_years": 1,
        "co_benefits": [
            "Groundwater recharge",
            "Flood buffering",
            "Biodiversity habitat",
            "Recreational amenity",
            "Cultural/heritage value"
        ],
        "constraints": [
            "Land encroachment issues",
            "Sewage contamination treatment",
            "Legal/ownership complexities",
            "Significant capital investment"
        ],
        "applicable_lulc": [50, 60, 80],
        "feature_effects": {
            "MNDWI":             {"delta_mode": "add", "value": 0.25, "range": [0.15, 0.40]},
            "NDVI":              {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.15, "range": [-0.25, -0.08]},
            "Dist_Water":        {"delta_mode": "multiply", "value": 0.30, "range": [0.15, 0.50]},
            "Humidity":          {"delta_mode": "add", "value": 3.0, "range": [1.0, 5.0]},
        },
        "physics_model": {
            "mechanism": "evaporative cooling + thermal mass",
            "evaporation_rate_mm_day": 6,
            "cooling_radius_m": 500,
            "latent_heat_flux_w_m2": 120,
        },
        "feasibility_score": 0.50,
        "scalability": "low",
        "indian_suitability": "very_high",
    },

    "urban_wetlands": {
        "id": "urban_wetlands",
        "name": "Urban Wetlands",
        "category": "blue",
        "description": "Constructed or restored wetland areas within city limits. "
                       "Combines water body cooling with vegetation cooling. "
                       "Also serves as natural wastewater treatment.",
        "cooling_potential_celsius": {"min": 1.5, "max": 4.0, "typical": 2.5},
        "cost_per_unit": {"value": 100000, "unit": "USD/hectare", "annual_maintenance": 5000},
        "implementation_time_months": {"min": 6, "max": 24},
        "lifespan_years": 40,
        "effectiveness_lag_years": 2,
        "co_benefits": [
            "Natural water filtration",
            "Flood attenuation",
            "Biodiversity habitat",
            "Carbon sequestration"
        ],
        "constraints": [
            "Large land area required",
            "Mosquito management needed",
            "Water source required",
            "Buffer zone from residential areas"
        ],
        "applicable_lulc": [60, 30, 80],
        "feature_effects": {
            "MNDWI":             {"delta_mode": "add", "value": 0.20, "range": [0.10, 0.30]},
            "NDVI":              {"delta_mode": "add", "value": 0.15, "range": [0.08, 0.25]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.12, "range": [-0.20, -0.06]},
            "Dist_Water":        {"delta_mode": "multiply", "value": 0.40, "range": [0.20, 0.60]},
            "Humidity":          {"delta_mode": "add", "value": 2.0, "range": [1.0, 4.0]},
            "Green_Space_Density": {"delta_mode": "add", "value": 0.12, "range": [0.06, 0.20]},
        },
        "physics_model": {
            "mechanism": "evaporative + vegetative cooling",
            "latent_heat_flux_w_m2": 100,
            "cooling_radius_m": 300,
        },
        "feasibility_score": 0.55,
        "scalability": "low",
        "indian_suitability": "high",
    },

    "ponds": {
        "id": "ponds",
        "name": "Ponds / Retention Basins",
        "category": "blue",
        "description": "Small to medium water bodies (0.01-1 hectare) created or "
                       "restored within neighborhoods. Provide localized cooling "
                       "and stormwater management.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.5},
        "cost_per_unit": {"value": 30000, "unit": "USD/pond", "annual_maintenance": 2000},
        "implementation_time_months": {"min": 3, "max": 12},
        "lifespan_years": 30,
        "effectiveness_lag_years": 0.5,
        "co_benefits": [
            "Stormwater retention",
            "Aesthetic value",
            "Microclimate regulation",
            "Aquaculture potential"
        ],
        "constraints": [
            "Land availability",
            "Water supply",
            "Safety fencing required",
            "Algae/maintenance management"
        ],
        "applicable_lulc": [50, 60, 30],
        "feature_effects": {
            "MNDWI":             {"delta_mode": "add", "value": 0.10, "range": [0.05, 0.18]},
            "Dist_Water":        {"delta_mode": "multiply", "value": 0.50, "range": [0.30, 0.70]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.05, "range": [-0.10, -0.02]},
            "Humidity":          {"delta_mode": "add", "value": 1.5, "range": [0.5, 3.0]},
        },
        "physics_model": {
            "mechanism": "evaporative cooling",
            "latent_heat_flux_w_m2": 50,
            "cooling_radius_m": 150,
        },
        "feasibility_score": 0.70,
        "scalability": "medium",
        "indian_suitability": "high",
    },

    "rain_gardens": {
        "id": "rain_gardens",
        "name": "Rain Gardens",
        "category": "blue",
        "description": "Shallow planted depressions that collect and filter rainwater "
                       "runoff from roofs and pavements. Combine green and blue "
                       "cooling mechanisms at neighborhood scale.",
        "cooling_potential_celsius": {"min": 0.3, "max": 1.5, "typical": 0.7},
        "cost_per_unit": {"value": 40, "unit": "USD/sqm", "annual_maintenance": 3},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 15,
        "effectiveness_lag_years": 1,
        "co_benefits": [
            "Stormwater infiltration",
            "Groundwater recharge",
            "Pollutant removal",
            "Beautification"
        ],
        "constraints": [
            "Soil permeability required",
            "Not for high water table areas",
            "Seasonal effectiveness varies"
        ],
        "applicable_lulc": [50, 30],
        "feature_effects": {
            "NDVI":              {"delta_mode": "add", "value": 0.06, "range": [0.03, 0.12]},
            "MNDWI":             {"delta_mode": "add", "value": 0.04, "range": [0.02, 0.08]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.05, "range": [-0.10, -0.02]},
            "NDBI":              {"delta_mode": "add", "value": -0.02, "range": [-0.04, -0.01]},
        },
        "physics_model": {
            "mechanism": "infiltration + evapotranspiration",
            "latent_heat_flux_w_m2": 25,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "permeable_pavements": {
        "id": "permeable_pavements",
        "name": "Permeable Pavements",
        "category": "blue",
        "description": "Porous concrete, permeable interlocking pavers, or porous "
                       "asphalt that allow rainwater infiltration. Reduce surface "
                       "temperature through evaporative cooling from subsurface moisture.",
        "cooling_potential_celsius": {"min": 0.3, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 45, "unit": "USD/sqm", "annual_maintenance": 3},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Stormwater infiltration",
            "Groundwater recharge",
            "Reduced flooding",
            "Reduced tire noise"
        ],
        "constraints": [
            "Not for heavy-traffic roads",
            "Clogging risk (requires cleaning)",
            "Subgrade must support infiltration",
            "Higher cost than conventional pavement"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.10, "range": [-0.18, -0.05]},
            "NDBI":              {"delta_mode": "add", "value": -0.03, "range": [-0.06, -0.01]},
            "MNDWI":             {"delta_mode": "add", "value": 0.02, "range": [0.01, 0.04]},
        },
        "physics_model": {
            "mechanism": "evaporative cooling from subsurface moisture",
            "latent_heat_flux_w_m2": 30,
            "infiltration_rate_mm_hr": 15,
        },
        "feasibility_score": 0.75,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "rainwater_harvesting": {
        "id": "rainwater_harvesting",
        "name": "Rainwater Harvesting",
        "category": "blue",
        "description": "Rooftop and surface rainwater collection, storage, and reuse. "
                       "Indirect cooling through groundwater recharge and water "
                       "availability for irrigation of green infrastructure.",
        "cooling_potential_celsius": {"min": 0.1, "max": 0.5, "typical": 0.3},
        "cost_per_unit": {"value": 2000, "unit": "USD/system", "annual_maintenance": 100},
        "implementation_time_months": {"min": 1, "max": 3},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Water security",
            "Reduced water bills",
            "Flood reduction",
            "Mandatory in many Indian cities"
        ],
        "constraints": [
            "Storage tank space needed",
            "First-flush diversion required",
            "Seasonal effectiveness (monsoon-dependent)"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.02, "range": [-0.05, 0.0]},
            "Humidity":          {"delta_mode": "add", "value": 0.5, "range": [0.2, 1.0]},
        },
        "physics_model": {
            "mechanism": "indirect cooling via water availability",
            "collection_rate_l_sqm_mm": 0.8,
        },
        "feasibility_score": 0.90,
        "scalability": "very_high",
        "indian_suitability": "very_high",
    },

    "water_channels": {
        "id": "water_channels",
        "name": "Water Channels / Urban Canals",
        "category": "blue",
        "description": "Open water channels through urban areas providing evaporative "
                       "cooling corridors. Historic Indian stepwells (baolis) and "
                       "canal systems provide cultural precedent.",
        "cooling_potential_celsius": {"min": 1.0, "max": 3.0, "typical": 1.8},
        "cost_per_unit": {"value": 200, "unit": "USD/linear meter", "annual_maintenance": 10},
        "implementation_time_months": {"min": 6, "max": 18},
        "lifespan_years": 30,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Transportation (some cases)",
            "Aesthetic/heritage value",
            "Linear green corridor potential",
            "Stormwater conveyance"
        ],
        "constraints": [
            "Water supply needed",
            "Contamination prevention",
            "Safety barriers required",
            "Right-of-way acquisition"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "MNDWI":             {"delta_mode": "add", "value": 0.08, "range": [0.04, 0.15]},
            "Dist_Water":        {"delta_mode": "multiply", "value": 0.50, "range": [0.30, 0.70]},
            "Humidity":          {"delta_mode": "add", "value": 1.5, "range": [0.8, 2.5]},
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.03, "range": [-0.06, -0.01]},
        },
        "physics_model": {
            "mechanism": "evaporative cooling corridor",
            "latent_heat_flux_w_m2": 60,
            "cooling_radius_m": 100,
        },
        "feasibility_score": 0.55,
        "scalability": "medium",
        "indian_suitability": "high",
    },

    "fountains": {
        "id": "fountains",
        "name": "Fountains / Water Features",
        "category": "blue",
        "description": "Active water features in public spaces that provide "
                       "localized evaporative cooling and psychological cooling "
                       "effect. Effective within 20-50m radius.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 10000, "unit": "USD/fountain", "annual_maintenance": 1500},
        "implementation_time_months": {"min": 1, "max": 6},
        "lifespan_years": 15,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Aesthetic enhancement",
            "White noise (masks traffic)",
            "Psychological cooling",
            "Tourism attraction"
        ],
        "constraints": [
            "Electricity for pumps",
            "Water supply",
            "Regular maintenance (filtration)",
            "Vandalism risk"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "MNDWI":             {"delta_mode": "add", "value": 0.02, "range": [0.01, 0.04]},
            "Humidity":          {"delta_mode": "add", "value": 1.0, "range": [0.5, 2.0]},
        },
        "physics_model": {
            "mechanism": "active evaporative cooling",
            "latent_heat_flux_w_m2": 40,
            "cooling_radius_m": 30,
        },
        "feasibility_score": 0.75,
        "scalability": "high",
        "indian_suitability": "medium",
    },

    "misting_systems": {
        "id": "misting_systems",
        "name": "Misting Systems",
        "category": "blue",
        "description": "High-pressure misting nozzles in public spaces (bus stops, "
                       "markets, pedestrian zones). Provide immediate 3-8°C perceived "
                       "temperature reduction through evaporative cooling of air.",
        "cooling_potential_celsius": {"min": 1.0, "max": 4.0, "typical": 2.5},
        "cost_per_unit": {"value": 5000, "unit": "USD/system", "annual_maintenance": 500},
        "implementation_time_months": {"min": 0.5, "max": 2},
        "lifespan_years": 10,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Immediate relief",
            "Low infrastructure requirement",
            "Portable/modular",
            "Dust suppression"
        ],
        "constraints": [
            "Water consumption (3-10 L/hr per nozzle)",
            "Humidity increase (uncomfortable if already humid)",
            "Legionella risk if poorly maintained",
            "Electricity for pump"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Humidity":          {"delta_mode": "add", "value": 5.0, "range": [2.0, 10.0]},
            "AirTemp":           {"delta_mode": "add", "value": -1.5, "range": [-3.0, -0.5]},
        },
        "physics_model": {
            "mechanism": "forced evaporative cooling of air",
            "droplet_size_micron": 10,
            "evaporation_rate_l_hr": 5,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "medium",
    },

    # =========================================================================
    # GREY INTERVENTIONS — Built environment modification
    # Mechanism: Wind flow optimization + shade engineering + morphology change
    # =========================================================================

    "wind_corridors": {
        "id": "wind_corridors",
        "name": "Wind Corridors",
        "category": "grey",
        "description": "Urban planning of aligned open spaces, road orientations, "
                       "and building heights to channel prevailing winds through "
                       "the city. Reduces stagnant heat pockets by 20-40%.",
        "cooling_potential_celsius": {"min": 1.0, "max": 3.5, "typical": 2.0},
        "cost_per_unit": {"value": 50000, "unit": "USD/corridor", "annual_maintenance": 1000},
        "implementation_time_months": {"min": 12, "max": 60},
        "lifespan_years": 50,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Improved air quality",
            "Natural ventilation for buildings",
            "Reduced AC dependency",
            "Pedestrian comfort"
        ],
        "constraints": [
            "Requires coordination with city planning",
            "Long implementation timeline",
            "May conflict with development density goals",
            "Wind tunnel effects need CFD modeling"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.30, "range": [1.15, 1.50]},
            "Building_Density":  {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
            "Surface_Roughness": {"delta_mode": "multiply", "value": 0.80, "range": [0.70, 0.90]},
        },
        "physics_model": {
            "mechanism": "wind channeling + turbulent mixing",
            "wind_speed_increase_pct": 30,
            "convective_heat_loss_increase_pct": 25,
        },
        "feasibility_score": 0.40,
        "scalability": "low",
        "indian_suitability": "high",
    },

    "building_spacing": {
        "id": "building_spacing",
        "name": "Building Spacing Optimization",
        "category": "grey",
        "description": "Ensuring adequate spacing between buildings for air flow "
                       "and sky view. H/W ratio optimization for street canyons. "
                       "Reduces trapped longwave radiation.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.5},
        "cost_per_unit": {"value": 0, "unit": "policy instrument", "annual_maintenance": 0},
        "implementation_time_months": {"min": 6, "max": 36},
        "lifespan_years": 50,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Better daylighting",
            "Natural ventilation",
            "Reduced canyon heating effect",
            "Improved living conditions"
        ],
        "constraints": [
            "Only for new development",
            "Reduces developable FAR",
            "Enforcement challenges",
            "Economic trade-offs"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Building_Density":  {"delta_mode": "multiply", "value": 0.80, "range": [0.70, 0.90]},
            "Building_Volume":   {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.15, "range": [1.05, 1.25]},
            "Surface_Roughness": {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
        },
        "physics_model": {
            "mechanism": "reduced canyon trapping + improved ventilation",
            "sky_view_factor_improvement": 0.15,
        },
        "feasibility_score": 0.45,
        "scalability": "low",
        "indian_suitability": "medium",
    },

    "street_canyon_optimization": {
        "id": "street_canyon_optimization",
        "name": "Street Canyon Optimization",
        "category": "grey",
        "description": "Optimizing the height-to-width (H/W) ratio of street canyons "
                       "for thermal comfort. In tropical Indian cities, deeper canyons "
                       "(H/W > 2) provide more shade but trap heat at night.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 0, "unit": "policy instrument", "annual_maintenance": 0},
        "implementation_time_months": {"min": 12, "max": 48},
        "lifespan_years": 50,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Daytime shading in summer",
            "Improved pedestrian comfort",
            "Architectural diversity"
        ],
        "constraints": [
            "Complex trade-offs (shade vs ventilation)",
            "New development only",
            "Requires urban design expertise"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Building_Height":   {"delta_mode": "multiply", "value": 0.90, "range": [0.80, 0.95]},
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.10, "range": [1.05, 1.20]},
        },
        "physics_model": {
            "mechanism": "canyon geometry optimization",
            "optimal_hw_ratio_tropical": 1.5,
        },
        "feasibility_score": 0.40,
        "scalability": "low",
        "indian_suitability": "medium",
    },

    "artificial_shading": {
        "id": "artificial_shading",
        "name": "Artificial Shading Structures",
        "category": "grey",
        "description": "Tensile fabric canopies, solar panel shade structures, "
                       "and shade sails over pedestrian areas, parking lots, and "
                       "markets. Immediate shade with potential for solar energy.",
        "cooling_potential_celsius": {"min": 1.0, "max": 4.0, "typical": 2.5},
        "cost_per_unit": {"value": 80, "unit": "USD/sqm", "annual_maintenance": 5},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 15,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "UV protection",
            "Solar energy generation (if PV panels)",
            "Rain shelter",
            "Immediate effect"
        ],
        "constraints": [
            "Wind resistance design required",
            "Structural foundation needed",
            "Aesthetic integration",
            "Does not address nighttime UHI"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "SolarRadiation":    {"delta_mode": "multiply", "value": 0.70, "range": [0.55, 0.85]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.88, "range": [0.80, 0.93]},
        },
        "physics_model": {
            "mechanism": "direct shade + reduced surface absorption",
            "shade_fraction": 0.80,
            "surface_temp_reduction_celsius": 15,
        },
        "feasibility_score": 0.85,
        "scalability": "high",
        "indian_suitability": "very_high",
    },

    "pergolas": {
        "id": "pergolas",
        "name": "Pergolas / Shade Corridors",
        "category": "grey",
        "description": "Open-roofed walkway structures that provide shade while "
                       "allowing air circulation. Can be combined with climbing "
                       "plants for additional evaporative cooling.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.5},
        "cost_per_unit": {"value": 100, "unit": "USD/sqm", "annual_maintenance": 5},
        "implementation_time_months": {"min": 1, "max": 3},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Aesthetic improvement",
            "Pedestrian comfort",
            "Green corridor potential",
            "Flexible design"
        ],
        "constraints": [
            "Structural design required",
            "Space requirements",
            "Maintenance of climbing plants"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "SolarRadiation":    {"delta_mode": "multiply", "value": 0.75, "range": [0.60, 0.85]},
            "NDVI":              {"delta_mode": "add", "value": 0.03, "range": [0.01, 0.06]},
        },
        "physics_model": {
            "mechanism": "partial shade + optional vegetation",
            "shade_fraction": 0.60,
        },
        "feasibility_score": 0.80,
        "scalability": "high",
        "indian_suitability": "high",
    },

    "jaali_structures": {
        "id": "jaali_structures",
        "name": "Jaali (Lattice Screen) Structures",
        "category": "grey",
        "description": "Traditional Indian lattice screens (jaalis) adapted for modern "
                       "urban use. Provide filtered shade while allowing wind passage. "
                       "Culturally rooted passive cooling strategy from Mughal architecture.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.0, "typical": 1.0},
        "cost_per_unit": {"value": 60, "unit": "USD/sqm", "annual_maintenance": 2},
        "implementation_time_months": {"min": 1, "max": 4},
        "lifespan_years": 25,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Cultural heritage preservation",
            "Privacy screening",
            "Wind velocity modulation",
            "Aesthetic/architectural value"
        ],
        "constraints": [
            "Skilled craftsmanship needed",
            "Material selection (stone vs concrete)",
            "Design integration with modern buildings"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "SolarRadiation":    {"delta_mode": "multiply", "value": 0.80, "range": [0.65, 0.90]},
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.05, "range": [1.02, 1.10]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.92, "range": [0.88, 0.96]},
        },
        "physics_model": {
            "mechanism": "filtered shade + wind passage",
            "shade_fraction": 0.50,
            "porosity": 0.40,
        },
        "feasibility_score": 0.75,
        "scalability": "medium",
        "indian_suitability": "very_high",
    },

    "building_orientation": {
        "id": "building_orientation",
        "name": "Building Orientation Optimization",
        "category": "grey",
        "description": "Orienting buildings to minimize solar heat gain on major "
                       "facades and maximize cross-ventilation. In India, east-west "
                       "elongation with north-south major facades is optimal.",
        "cooling_potential_celsius": {"min": 0.3, "max": 1.5, "typical": 0.8},
        "cost_per_unit": {"value": 0, "unit": "design parameter", "annual_maintenance": 0},
        "implementation_time_months": {"min": 0, "max": 0},
        "lifespan_years": 50,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Natural daylighting",
            "Cross ventilation",
            "Solar PV optimization",
            "No additional cost"
        ],
        "constraints": [
            "New construction only",
            "Plot shape may limit options",
            "Zoning/setback rules"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "SolarRadiation":    {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.10, "range": [1.05, 1.18]},
            "Anthropogenic_Heat": {"delta_mode": "multiply", "value": 0.90, "range": [0.85, 0.95]},
        },
        "physics_model": {
            "mechanism": "reduced solar heat gain + improved ventilation",
            "optimal_orientation_india": "N-S major axis",
        },
        "feasibility_score": 0.60,
        "scalability": "medium",
        "indian_suitability": "high",
    },

    "ventilation_corridors": {
        "id": "ventilation_corridors",
        "name": "Ventilation Corridors",
        "category": "grey",
        "description": "Dedicated open-air corridors connecting city areas to allow "
                       "air flow from cooler zones (parks, water bodies, rural fringe) "
                       "into dense urban cores.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.5},
        "cost_per_unit": {"value": 30000, "unit": "USD/corridor", "annual_maintenance": 500},
        "implementation_time_months": {"min": 12, "max": 48},
        "lifespan_years": 50,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Air quality improvement",
            "Pedestrian/cyclist pathway",
            "Green belt potential",
            "Noise buffering"
        ],
        "constraints": [
            "Requires long-term urban planning",
            "Land acquisition challenges",
            "Development pressure",
            "Coordination across jurisdictions"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "WindSpeed":         {"delta_mode": "multiply", "value": 1.20, "range": [1.10, 1.35]},
            "Building_Density":  {"delta_mode": "multiply", "value": 0.90, "range": [0.80, 0.95]},
            "Surface_Roughness": {"delta_mode": "multiply", "value": 0.85, "range": [0.75, 0.92]},
        },
        "physics_model": {
            "mechanism": "advective cooling via air exchange",
            "wind_speed_increase_pct": 20,
        },
        "feasibility_score": 0.35,
        "scalability": "low",
        "indian_suitability": "medium",
    },

    "impervious_surface_reduction": {
        "id": "impervious_surface_reduction",
        "name": "Impervious Surface Reduction",
        "category": "grey",
        "description": "Replacing paved/sealed surfaces with permeable or vegetated "
                       "alternatives. Reduces heat storage capacity of urban fabric "
                       "and allows soil moisture evaporation.",
        "cooling_potential_celsius": {"min": 0.5, "max": 2.5, "typical": 1.2},
        "cost_per_unit": {"value": 30, "unit": "USD/sqm", "annual_maintenance": 2},
        "implementation_time_months": {"min": 2, "max": 8},
        "lifespan_years": 20,
        "effectiveness_lag_years": 0,
        "co_benefits": [
            "Stormwater management",
            "Groundwater recharge",
            "Reduced flooding",
            "Soil health improvement"
        ],
        "constraints": [
            "Load-bearing capacity for vehicle areas",
            "Maintenance complexity",
            "Cost vs conventional surfaces"
        ],
        "applicable_lulc": [50],
        "feature_effects": {
            "Impervious_Frac":   {"delta_mode": "add", "value": -0.15, "range": [-0.25, -0.08]},
            "NDBI":              {"delta_mode": "add", "value": -0.05, "range": [-0.10, -0.02]},
            "NDVI":              {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
            "Albedo":            {"delta_mode": "add", "value": 0.05, "range": [0.02, 0.10]},
        },
        "physics_model": {
            "mechanism": "reduced heat storage + evaporative cooling",
            "thermal_admittance_reduction_pct": 25,
        },
        "feasibility_score": 0.75,
        "scalability": "high",
        "indian_suitability": "high",
    },
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_all_interventions() -> Dict:
    """Return the full intervention library."""
    return INTERVENTION_LIBRARY


def get_interventions_by_category(category: str) -> Dict:
    """Return interventions filtered by category (green/white/blue/grey)."""
    return {k: v for k, v in INTERVENTION_LIBRARY.items()
            if v['category'] == category.lower()}


def get_intervention(intervention_id: str) -> Optional[Dict]:
    """Return a single intervention by ID."""
    return INTERVENTION_LIBRARY.get(intervention_id)


def get_intervention_ids() -> List[str]:
    """Return all intervention IDs."""
    return list(INTERVENTION_LIBRARY.keys())


def get_category_summary() -> Dict:
    """Return a summary of interventions per category."""
    summary = {}
    for iid, data in INTERVENTION_LIBRARY.items():
        cat = data['category']
        if cat not in summary:
            summary[cat] = {'count': 0, 'interventions': [], 'avg_cooling': 0}
        summary[cat]['count'] += 1
        summary[cat]['interventions'].append(data['name'])
        summary[cat]['avg_cooling'] += data['cooling_potential_celsius']['typical']
    for cat in summary:
        summary[cat]['avg_cooling'] = round(
            summary[cat]['avg_cooling'] / summary[cat]['count'], 2
        )
    return summary


def get_feature_to_interventions_map() -> Dict[str, List[str]]:
    """Build reverse mapping: feature → list of interventions that affect it."""
    mapping = {}
    for iid, data in INTERVENTION_LIBRARY.items():
        for feat in data['feature_effects']:
            if feat not in mapping:
                mapping[feat] = []
            mapping[feat].append(iid)
    return mapping


def export_library_json(filepath: str):
    """Export the full intervention library as JSON."""
    output = {
        'version': '1.0.0',
        'total_interventions': len(INTERVENTION_LIBRARY),
        'categories': get_category_summary(),
        'feature_to_intervention_map': get_feature_to_interventions_map(),
        'interventions': {}
    }
    for iid, data in INTERVENTION_LIBRARY.items():
        # Remove non-serializable fields
        clean = {k: v for k, v in data.items()}
        output['interventions'][iid] = clean

    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return filepath


if __name__ == '__main__':
    # Print library summary
    print('=' * 70)
    print('  URBAN COOLING INTERVENTION LIBRARY')
    print('=' * 70)

    summary = get_category_summary()
    for cat, info in summary.items():
        print(f'\n  [{cat.upper()}] ({info["count"]} interventions, '
              f'avg cooling: {info["avg_cooling"]}°C)')
        for name in info['interventions']:
            print(f'    • {name}')

    print(f'\n  Total: {len(INTERVENTION_LIBRARY)} interventions')
    print(f'  Features affected: {len(get_feature_to_interventions_map())}')

    # Export
    out = export_library_json(
        os.path.join(os.path.dirname(__file__), '..', 'outputs',
                     'intervention_library.json')
    )
    print(f'\n  Exported to: {out}')
