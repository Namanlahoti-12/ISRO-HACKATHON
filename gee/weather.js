// ============================================================================
// MODULE: weather.js — ERA5-Land Weather Variables
// ============================================================================
// Extracts 8 weather variables from ERA5-Land reanalysis (~11 km, hourly).
// All variables are averaged over the user-defined date range.
//
// Variables:
//   1. Air Temperature (°C) — temperature_2m
//   2. Relative Humidity (%) — computed via Magnus formula from dewpoint
//   3. Wind Speed (m/s) — sqrt(U² + V²)
//   4. Wind Direction (°) — atan2(U, V) converted to meteorological convention
//   5. Solar Radiation (W/m²) — surface_solar_radiation_downwards_hourly
//   6. Cloud Cover (fraction) — from ERA5 Daily (not in ERA5-Land)
//   7. Surface Pressure (hPa) — surface_pressure
//   8. Rainfall (mm) — total_precipitation_hourly
//
// References:
//   - Muñoz Sabater (2019) for ERA5-Land
//   - Alduchov & Eskridge (1996) for Magnus formula coefficients
// ============================================================================

function processERA5(studyArea, startDate, endDate) {
  var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
    .filterBounds(studyArea)
    .filterDate(startDate, endDate);

  // --- Air Temperature (K → °C) ---
  var airTempK = era5.select('temperature_2m').mean();
  var airTempC = airTempK.subtract(273.15).rename('AirTemp');

  // --- Relative Humidity (Magnus formula) ---
  var dewpointK = era5.select('dewpoint_temperature_2m').mean();
  var dewpointC = dewpointK.subtract(273.15);
  var airForRH  = airTempK.subtract(273.15);
  var num = dewpointC.multiply(17.625).divide(dewpointC.add(243.04));
  var den = airForRH.multiply(17.625).divide(airForRH.add(243.04));
  var humidity = num.subtract(den).exp().multiply(100)
    .clamp(0, 100).rename('Humidity');

  // --- Wind Speed & Direction ---
  var windU = era5.select('u_component_of_wind_10m').mean();
  var windV = era5.select('v_component_of_wind_10m').mean();
  var windSpeed = windU.pow(2).add(windV.pow(2)).sqrt().rename('WindSpeed');
  // Meteorological convention: direction FROM which wind blows.
  var windDir = windU.atan2(windV)
    .multiply(180 / Math.PI).add(180).mod(360).rename('WindDirection');

  // --- Solar Radiation (J/m² → W/m² average) ---
  // Hourly accumulation in J/m². Divide by 3600 to get mean W/m².
  var solarRad = era5.select('surface_solar_radiation_downwards_hourly')
    .mean().divide(3600).rename('SolarRadiation');

  // --- Surface Pressure (Pa → hPa) ---
  var pressure = era5.select('surface_pressure')
    .mean().divide(100).rename('Pressure');

  // --- Rainfall (m/hour → mm/day, accumulated) ---
  var rainfall = era5.select('total_precipitation_hourly')
    .sum().multiply(1000).rename('Rainfall');

  // Combine all weather bands into one image.
  return airTempC
    .addBands(humidity)
    .addBands(windSpeed)
    .addBands(windDir)
    .addBands(solarRad)
    .addBands(pressure)
    .addBands(rainfall)
    .clip(studyArea);
}

// --- Cloud Cover from ERA5 Daily (separate collection) ---
// ERA5-Land does NOT include cloud cover. We use ERA5 atmospheric.
function getCloudCover(studyArea, startDate, endDate) {
  // Note: ECMWF/ERA5/DAILY may not include total_cloud_cover in GEE.
  // If unavailable, this returns a constant zero image.
  try {
    var era5daily = ee.ImageCollection('ECMWF/ERA5/DAILY')
      .filterBounds(studyArea)
      .filterDate(startDate, endDate);
    return era5daily.select('total_cloud_cover')
      .mean().clip(studyArea).rename('CloudCover');
  } catch(e) {
    // Fallback: return a masked constant (flag as unavailable)
    return ee.Image.constant(0).rename('CloudCover')
      .clip(studyArea).updateMask(ee.Image.constant(0));
  }
}
