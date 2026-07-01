import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { useConfig, useGridData } from '../services/api';
import { useGeocoder } from '../hooks/useGeocoder';
import { exportGeoJSON, exportCSV, exportPNG } from '../utils/export';

export function Header() {
  const darkMode = useStore((s) => s.darkMode);
  const toggleDark = useStore((s) => s.toggleDarkMode);
  const coords = useStore((s) => s.cursorCoords);
  const mapReady = useStore((s) => s.mapReady);
  const setFlyTo = useStore((s) => s.setFlyTo);
  const { data: config } = useConfig();
  const { data: gridData } = useGridData();

  const [searchVal, setSearchVal] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { geocode, flyToResult, loading: geoLoading, suggestions, clearSuggestions } = useGeocoder();

  const doExportGeoJSON = () => { if (gridData) exportGeoJSON(gridData.pixels); };
  const doExportCSV = () => { if (gridData) exportCSV(gridData.pixels); };
  const doExportPNG = () => {
    const canvas = document.querySelector<HTMLCanvasElement>('.maplibregl-canvas');
    exportPNG(canvas);
  };

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      await geocode(searchVal);
      if (suggestions.length) setShowDropdown(true);
    }
    if (e.key === 'Escape') {
      setShowDropdown(false);
      clearSuggestions();
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchVal(e.target.value);
    if (!e.target.value) {
      clearSuggestions();
      setShowDropdown(false);
    }
  };

  useEffect(() => {
    if (suggestions.length > 0) setShowDropdown(true);
    else setShowDropdown(false);
  }, [suggestions]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSuggestionClick = (s: { lat: number; lng: number; display_name?: string }) => {
    flyToResult(s);
    setSearchVal(s.display_name?.split(',')[0] ?? '');
    setShowDropdown(false);
  };

  return (
    <header className="header">
      {/* Left: Logo + Status */}
      <div className="header-left">
        <div className="logo-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="#ef4444"/>
            <circle cx="12" cy="9" r="2.5" fill="#fff"/>
          </svg>
        </div>
        <div className="logo-text">
          <h1>Urban Heat AI</h1>
          <span className="sub">ISRO Hackathon · MapLibre GIS</span>
        </div>
        <div className="header-badges">
          <span className="badge">
            <span className={`dot ${mapReady ? 'dot-ok' : 'dot-warn'}`} />
            {mapReady ? 'Live' : 'Connecting'}
          </span>
          {config && (
            <span className="badge badge-info">
              <span className="dot dot-blue" />
              {config.total_pixels?.toLocaleString()} cells
            </span>
          )}
        </div>
      </div>

      {/* Center: Search */}
      <div className="header-center">
        <div className="search-wrapper">
          <div className={`search-box ${geoLoading ? 'loading' : ''}`}>
            <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={searchVal}
              placeholder="Search city, address, lat/lng, pincode..."
              onChange={handleSearchChange}
              onKeyDown={handleKeyDown}
              autoComplete="off"
            />
            {geoLoading && <span className="search-spinner" />}
            {searchVal && (
              <button
                className="search-clear"
                onClick={() => { setSearchVal(''); clearSuggestions(); setShowDropdown(false); }}
              >✕</button>
            )}
          </div>
          {showDropdown && suggestions.length > 0 && (
            <div className="search-dropdown" ref={dropdownRef}>
              {suggestions.map((s, i) => (
                <div key={i} className="search-suggestion" onClick={() => handleSuggestionClick(s)}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                  </svg>
                  <span>{s.display_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right: Controls */}
      <div className="header-right">
        <div className="coords-display" title="Cursor coordinates">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {coords ? `${coords.lat.toFixed(5)}°N  ${coords.lng.toFixed(5)}°E` : '—  —'}
        </div>

        <div className="header-divider" />

        <div className="export-group">
          <span className="export-label">Export</span>
          <button className="btn-sm" onClick={doExportPNG} title="Export map as PNG">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            PNG
          </button>
          <button className="btn-sm" onClick={doExportGeoJSON} title="Export as GeoJSON">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
            </svg>
            GeoJSON
          </button>
          <button className="btn-sm" onClick={doExportCSV} title="Export as CSV">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
            </svg>
            CSV
          </button>
        </div>

        <div className="header-divider" />

        <button
          className={`btn-icon ${!darkMode ? 'active' : ''}`}
          onClick={toggleDark}
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {darkMode ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
