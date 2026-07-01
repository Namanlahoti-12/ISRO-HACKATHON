"""
tile_server.py - XYZ Raster Tile Server for GeoTIFF layers
============================================================
Serves 256x256 PNG tiles from GeoTIFF rasters at /api/tiles/<layer>/<z>/<x>/<y>.png
Each tile is rendered with a colour ramp appropriate to the layer.

Designed to be imported by app.py and registered as Flask routes.
"""

import io
import math
import os

import numpy as np

try:
    import rasterio
    from rasterio.windows import from_bounds as window_from_bounds
except ImportError:
    rasterio = None

# We use PIL for fast RGBA image generation (no matplotlib overhead per tile)
try:
    from PIL import Image
except ImportError:
    Image = None

TILE_SIZE = 256

# ---------------------------------------------------------------------------
# Colour ramp definitions: layer_key -> (vmin, vmax, [(stop, r, g, b), ...])
# ---------------------------------------------------------------------------
def _hex(c):
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

def _build_ramp(colors, vmin, vmax):
    """Build a list of (stop, r, g, b) from hex colour list."""
    n = len(colors)
    stops = []
    for i, c in enumerate(colors):
        r, g, b = _hex(c)
        t = i / max(n - 1, 1)
        stops.append((t, r, g, b))
    return vmin, vmax, stops


# Colour ramps matching the frontend layerConfig palettes
COLOUR_RAMPS = {
    'HeatScore_Predicted': _build_ramp(
        ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff8000', '#ff0000', '#800000'], 38, 50),
    'HeatScore_Predicted_simulated': _build_ramp(
        ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff8000', '#ff0000', '#800000'], 38, 50),
    'HeatScore_Predicted_diff': _build_ramp(
        ['#2166ac', '#67a9cf', '#f7f7f7', '#ef8a62', '#b2182b'], -10, 10),
    'LST':  _build_ramp(
        ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff8000', '#ff0000', '#800000'], 38, 50),
    'AirTemp': _build_ramp(['#2563eb', '#67e8f9', '#fef08a', '#fb923c', '#dc2626'], 25, 45),
    'UHI_Intensity': _build_ramp(['#1d4ed8', '#22c55e', '#facc15', '#f97316', '#dc2626'], -5, 10),
    'UTFVI': _build_ramp(['#1d4ed8', '#22c55e', '#facc15', '#dc2626'], -1, 1),
    'NDVI': _build_ramp(['#7c2d12', '#facc15', '#bbf7d0', '#22c55e', '#14532d'], -0.1, 0.8),
    'NDBI': _build_ramp(['#fef9c3', '#fb923c', '#dc2626'], -0.3, 0.35),
    'NDWI': _build_ramp(['#ffffff', '#bfdbfe', '#2563eb', '#1e3a8a'], -0.5, 0.6),
    'MNDWI': _build_ramp(['#e0f2fe', '#60a5fa', '#1d4ed8'], -0.6, 0.7),
    'Population_Density': _build_ramp(['#fef9c3', '#fb923c', '#dc2626'], 0, 500),
    'Building_Density': _build_ramp(['#9ca3af', '#fb923c', '#dc2626'], 0, 90),
    'Building_Height': _build_ramp(['#e5e7eb', '#facc15', '#f97316', '#7f1d1d'], 0, 30),
    'Road_Density_Proxy': _build_ramp(['#d1d5db', '#f97316', '#b91c1c'], 0, 1),
    'Anthropogenic_Heat': _build_ramp(['#fef9c3', '#fb923c', '#dc2626', '#7f1d1d'], 0, 1),
    'Nighttime_Lights': _build_ramp(['#2e1065', '#7e22ce', '#facc15'], 0, 63),
    'Impervious_Frac': _build_ramp(['#9ca3af', '#fb923c', '#dc2626'], 0, 1),
    'Tree_Cover_Pct': _build_ramp(['#bbf7d0', '#22c55e', '#14532d'], 0, 80),
    'Dist_Water': _build_ramp(['#1d4ed8', '#bfdbfe', '#ffffff'], 0, 10000),
    'Dist_Green': _build_ramp(['#14532d', '#bbf7d0', '#ffffff'], 0, 5000),
    'Green_Space_Density': _build_ramp(['#dcfce7', '#22c55e', '#14532d'], 0, 1),
    'Albedo': _build_ramp(['#111827', '#6b7280', '#d1d5db', '#ffffff'], 0.05, 0.4),
    'Humidity': _build_ramp(['#facc15', '#22c55e', '#1d4ed8'], 20, 70),
    'WindSpeed': _build_ramp(['#7e22ce', '#2563eb', '#06b6d4'], 0, 6),
    'WindDirection': _build_ramp(['#7e22ce', '#facc15', '#06b6d4', '#22c55e'], 0, 360),
    'SolarRadiation': _build_ramp(['#facc15', '#fb923c', '#dc2626'], 0, 1000),
    'Elevation': _build_ramp(['#166534', '#facc15', '#a16207', '#78716c'], 150, 350),
    'Slope': _build_ramp(['#d1d5db', '#f97316', '#b91c1c'], 0, 15),
    'LULC_ESA': _build_ramp(['#14532d', '#d95f0e', '#1d4ed8', '#d1d5db'], 10, 80),
    'LULC_DW': _build_ramp(['#14532d', '#d95f0e', '#1d4ed8', '#d1d5db'], 0, 7),
    'SAVI': _build_ramp(['#7c2d12', '#facc15', '#22c55e', '#14532d'], -0.1, 0.8),
    'Building_Volume': _build_ramp(['#e5e7eb', '#facc15', '#dc2626'], 0, 500),
    'Surface_Roughness': _build_ramp(['#d1d5db', '#f97316', '#b91c1c'], 0, 1),
    'UTCI_Approx': _build_ramp(['#1e40af', '#06b6d4', '#facc15', '#f97316', '#b91c1c'], 20, 50),
    'LULC_Derived': _build_ramp(['#14532d', '#d95f0e', '#1d4ed8', '#d1d5db'], 0, 3),
}


def _colourize(t, stops):
    """Interpolate colour from normalised t in [0,1] using stops list."""
    if t <= stops[0][0]:
        return stops[0][1], stops[0][2], stops[0][3]
    if t >= stops[-1][0]:
        return stops[-1][1], stops[-1][2], stops[-1][3]
    for i in range(len(stops) - 1):
        t0, r0, g0, b0 = stops[i]
        t1, r1, g1, b1 = stops[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / max(t1 - t0, 1e-9)
            return (
                int(r0 + (r1 - r0) * f),
                int(g0 + (g1 - g0) * f),
                int(b0 + (b1 - b0) * f),
            )
    return stops[-1][1], stops[-1][2], stops[-1][3]


# Vectorized colourization using lookup table for speed
def _build_lut(vmin, vmax, stops, n=4096):
    """Build a 256x4 RGBA lookup table from vmin/vmax and stops."""
    lut = np.zeros((n, 4), dtype=np.uint8)
    for i in range(n):
        t = i / max(n - 1, 1)
        r, g, b = _colourize(t, stops)
        lut[i] = [r, g, b, 255]
    return lut, vmin, vmax


# Cache LUTs
_LUT_CACHE = {}

def _get_lut(layer_key):
    if layer_key not in _LUT_CACHE:
        ramp = COLOUR_RAMPS.get(layer_key)
        if ramp is None:
            # Default: grey ramp
            ramp = _build_ramp(['#333333', '#cccccc'], 0, 1)
        vmin, vmax, stops = ramp
        lut, _, _ = _build_lut(vmin, vmax, stops)
        _LUT_CACHE[layer_key] = (lut, vmin, vmax)
    return _LUT_CACHE[layer_key]


# ---------------------------------------------------------------------------
# Tile math: convert XYZ tile coordinates to lat/lng bounds
# ---------------------------------------------------------------------------
def tile_bounds(z, x, y):
    """Return (west, south, east, north) in EPSG:4326 for tile z/x/y."""
    n = 2 ** z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return west, south, east, north


# ---------------------------------------------------------------------------
# Raster cache: keep open file handles for fast reading
# ---------------------------------------------------------------------------
_RASTER_CACHE = {}

def _open_raster(path):
    """Open raster and cache the dataset handle."""
    if path not in _RASTER_CACHE:
        if not os.path.exists(path):
            return None
        _RASTER_CACHE[path] = rasterio.open(path)
    return _RASTER_CACHE[path]

def close_all_rasters():
    """Close all cached raster handles."""
    for ds in _RASTER_CACHE.values():
        ds.close()
    _RASTER_CACHE.clear()


# ---------------------------------------------------------------------------
# Core: render a single tile
# ---------------------------------------------------------------------------
def render_tile(raster_path, layer_key, z, x, y):
    """
    Render a 256x256 RGBA PNG tile for the given raster layer at z/x/y.
    Returns bytes of a PNG image, or None if tile is outside raster bounds.
    """
    if rasterio is None or Image is None:
        return None

    ds = _open_raster(raster_path)
    if ds is None:
        return None

    # Tile bounds in EPSG:4326
    west, south, east, north = tile_bounds(z, x, y)

    # Check if tile intersects raster
    rb = ds.bounds
    if east <= rb.left or west >= rb.right or north <= rb.bottom or south >= rb.top:
        return None  # tile completely outside raster

    # Clamp to raster bounds
    west_c  = max(west, rb.left)
    south_c = max(south, rb.bottom)
    east_c  = min(east, rb.right)
    north_c = min(north, rb.top)

    try:
        window = window_from_bounds(west_c, south_c, east_c, north_c, ds.transform)
        # Read at native resolution within the window
        data = ds.read(1, window=window, boundless=True)
    except Exception:
        return None

    if data.size == 0:
        return None

    # Resample to TILE_SIZE x TILE_SIZE
    # Calculate the pixel coordinates within the 256x256 tile
    tile_w = east - west
    tile_h = north - south

    # How much of the 256px tile does the clamped region cover?
    px_left   = int((west_c - west) / tile_w * TILE_SIZE) if tile_w > 0 else 0
    px_right  = int((east_c - west) / tile_w * TILE_SIZE) if tile_w > 0 else TILE_SIZE
    px_top    = int((north - north_c) / tile_h * TILE_SIZE) if tile_h > 0 else 0
    px_bottom = int((north - south_c) / tile_h * TILE_SIZE) if tile_h > 0 else TILE_SIZE

    out_w = max(px_right - px_left, 1)
    out_h = max(px_bottom - px_top, 1)

    # Resize data to fill its portion of the tile
    data_img = Image.fromarray(data.astype(np.float32), mode='F')
    data_resized = np.array(data_img.resize((out_w, out_h), Image.NEAREST), dtype=np.float32)

    # Apply colour ramp using LUT
    lut, vmin, vmax = _get_lut(layer_key)
    lut_size = len(lut)

    # Normalise values to [0, lut_size-1]
    vrange = vmax - vmin
    if vrange < 1e-9:
        vrange = 1.0
    indices = ((data_resized - vmin) / vrange * (lut_size - 1)).astype(np.int32)
    indices = np.clip(indices, 0, lut_size - 1)

    # Create RGBA from LUT
    rgba_region = lut[indices]

    # Set nodata pixels to transparent
    nodata_mask = np.isnan(data_resized) | (data_resized == ds.nodata if ds.nodata is not None else np.zeros_like(data_resized, dtype=bool))
    rgba_region[nodata_mask] = [0, 0, 0, 0]

    # Place into full tile (rest is transparent)
    tile_rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    tile_rgba[px_top:px_top + out_h, px_left:px_left + out_w] = rgba_region

    # Encode as PNG
    img = Image.fromarray(tile_rgba, 'RGBA')
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=False)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Flask integration: register tile routes on an app
# ---------------------------------------------------------------------------
def register_tile_routes(flask_app, raster_dir):
    """Register /api/tiles/<layer>/<z>/<x>/<y>.png route on the Flask app."""
    from flask import Response, abort

    @flask_app.route('/api/tiles/<layer_key>/<int:z>/<int:x>/<int:y>.png')
    def serve_tile(layer_key, z, x, y):
        # Map layer_key to raster file
        # Special handling: HeatScore_Predicted is the AI output
        # Others map directly to <layer_key>.tif
        raster_name = f'{layer_key}.tif'
        raster_path = os.path.join(raster_dir, raster_name)

        if not os.path.exists(raster_path):
            abort(404)

        png_bytes = render_tile(raster_path, layer_key, z, x, y)
        if png_bytes is None:
            # Return a transparent 1x1 PNG for out-of-bounds tiles
            return Response(
                _transparent_png(),
                mimetype='image/png',
                headers={'Cache-Control': 'public, max-age=86400'},
            )

        return Response(
            png_bytes,
            mimetype='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @flask_app.route('/api/tiles/available')
    def list_available_tiles():
        """List all available raster layers for tile serving."""
        layers = []
        if os.path.isdir(raster_dir):
            for f in sorted(os.listdir(raster_dir)):
                if f.endswith('.tif'):
                    key = f[:-4]
                    layers.append({
                        'key': key,
                        'has_ramp': key in COLOUR_RAMPS,
                    })
        return {'layers': layers}


_TRANSPARENT_PNG = None

def _transparent_png():
    """Return a 1x1 transparent PNG (cached)."""
    global _TRANSPARENT_PNG
    if _TRANSPARENT_PNG is None:
        img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        _TRANSPARENT_PNG = buf.getvalue()
    return _TRANSPARENT_PNG
