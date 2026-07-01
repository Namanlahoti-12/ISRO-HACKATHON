import { useMemo, useState } from 'react';
import { useStore } from '../store/useStore';
import { useConfig, useGridData } from '../services/api';
import { LAYERS, LAYER_GROUPS, getLayerDef } from '../maps/layerConfig';
import { gradientCSS } from '../utils/colors';
import { exportGeoJSON, exportCSV } from '../utils/export';

export function Sidebar() {
  const {
    activeLayer, setActiveLayer, opacity, setOpacity,
    sidebarOpen, setSidebarOpen, hiddenLayers, toggleHiddenLayer,
    simView, spatialResult, gridView, toggleGridView,
  } = useStore();

  const { data: config } = useConfig();
  const { data: gridData } = useGridData();

  const [expandedSection, setExpandedSection] = useState<string>('layers');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(Object.keys(LAYER_GROUPS))   // all groups open by default
  );
  const [search, setSearch] = useState('');

  const def = getLayerDef(activeLayer);
  const stats = useMemo(() => {
    if (activeLayer === 'HeatScore_Predicted' && spatialResult?.pixels?.length && simView !== 'before') {
      const values = spatialResult.pixels.map((p) => simView === 'after' ? p.a : p.d);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
      const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
      return { min, max, mean, std: Math.sqrt(variance) };
    }
    return gridData?.stats?.[activeLayer];
  }, [activeLayer, gridData?.stats, simView, spatialResult]);
  const legendColors = activeLayer === 'HeatScore_Predicted' && spatialResult?.pixels?.length && simView === 'diff'
    ? ['#b2182b', '#ef8a62', '#f7f7f7', '#67a9cf', '#2166ac']
    : def?.colors ?? [];

  const toggleSection = (s: string) => setExpandedSection(expandedSection === s ? '' : s);

  const toggleGroup = (g: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(g)) next.delete(g); else next.add(g);
      return next;
    });
  };

  const filteredLayers = LAYERS.filter((l) =>
    l.name.toLowerCase().includes(search.toLowerCase()) ||
    l.key.toLowerCase().includes(search.toLowerCase())
  );

  // Group layers
  const grouped = new Map<string, typeof LAYERS>();
  for (const l of filteredLayers) {
    const g = l.group ?? 'other';
    if (!grouped.has(g)) grouped.set(g, []);
    grouped.get(g)!.push(l);
  }

  const doDownloadLayer = () => { if (gridData) exportGeoJSON(gridData.pixels); };
  const doDownloadCSV = () => { if (gridData) exportCSV(gridData.pixels); };

  const EyeOn = () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  );
  const EyeOff = () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );

  return (
    <aside className={`panel sidebar ${sidebarOpen ? '' : 'closed'}`}>
      <div className="panel-head" onClick={() => setSidebarOpen(!sidebarOpen)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
          </svg>
          Layer Manager
          <span style={{ marginLeft: 'auto', fontSize: 10, opacity: 0.5 }}>{LAYERS.length} layers</span>
        </div>
        <svg
          width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ transform: sidebarOpen ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform .2s' }}
        >
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </div>

      <div className="panel-body">

        {/* Search */}
        <div className="layer-search-wrap">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            className="layer-search"
            placeholder={`Search ${LAYERS.length} layers...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button style={{ background:'none',border:'none',cursor:'pointer',opacity:0.6,fontSize:10 }}
              onClick={() => setSearch('')}>✕</button>
          )}
        </div>

        {/* Active Layer Badge */}
        {def && (
          <div className="active-layer-badge">
            <span style={{ color: def.colors[def.colors.length - 1] }}>{def.icon}</span>
            <span>{def.name}</span>
            <span className="layer-unit" style={{ marginLeft: 'auto' }}>{def.unit}</span>
          </div>
        )}

        {/* Layers Section */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('layers')}>
            <span>Data Layers ({filteredLayers.length})</span>
            <span>{expandedSection === 'layers' ? '▾' : '▸'}</span>
          </div>

          {expandedSection === 'layers' && (
            <div className="layer-list">
              {Array.from(grouped.entries()).map(([groupKey, groupLayers]) => {
                const groupLabel = LAYER_GROUPS[groupKey] ?? groupKey;
                const isGroupExpanded = expandedGroups.has(groupKey);
                return (
                  <div key={groupKey} className="layer-group">
                    <div
                      className="layer-group-header"
                      onClick={() => toggleGroup(groupKey)}
                    >
                      <span>{groupLabel}</span>
                      <span style={{ opacity: 0.5, fontSize: 9 }}>
                        {isGroupExpanded ? '▾' : '▸'} {groupLayers.length}
                      </span>
                    </div>
                    {isGroupExpanded && groupLayers.map((l) => (
                      <div
                        key={l.key}
                        id={`layer-${l.key}`}
                        className={`layer-item ${activeLayer === l.key ? 'active' : ''} ${hiddenLayers.has(l.key) ? 'hidden-layer' : ''}`}
                        onClick={() => setActiveLayer(l.key)}
                      >
                        <button
                          className={`layer-vis-btn ${hiddenLayers.has(l.key) ? 'invisible' : ''}`}
                          onClick={(e) => { e.stopPropagation(); toggleHiddenLayer(l.key); }}
                          title={hiddenLayers.has(l.key) ? 'Show' : 'Hide'}
                        >
                          {hiddenLayers.has(l.key) ? <EyeOff /> : <EyeOn />}
                        </button>

                        <div
                          className="layer-swatch"
                          style={{ background: `linear-gradient(135deg, ${l.colors[0]}, ${l.colors[l.colors.length - 1]})` }}
                        />

                        <span className="layer-name">{l.icon} {l.name}</span>
                        <span className="layer-unit">{l.unit}</span>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Opacity */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('opacity')}>
            <span>Opacity</span>
            <span>{expandedSection === 'opacity' ? '▾' : '▸'}</span>
          </div>
          {expandedSection === 'opacity' && (
            <div className="slider-row">
              <div className="opacity-preview" style={{ opacity }} />
              <input
                type="range" min={10} max={100}
                value={Math.round(opacity * 100)}
                onChange={(e) => setOpacity(+e.target.value / 100)}
              />
              <span className="slider-val">{Math.round(opacity * 100)}%</span>
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('legend')}>
            <span>Legend</span>
            <span>{expandedSection === 'legend' ? '▾' : '▸'}</span>
          </div>
          {expandedSection === 'legend' && def && stats && (
            <div className="legend-block">
              <div className="legend-title">
                {def.icon} {def.name}
                <span className="legend-unit">{def.unit}</span>
              </div>
              <div className="legend-gradient-wrap">
                <div className="legend-bar" style={{ background: gradientCSS(legendColors) }} />
                <div className="legend-ticks">
                  {[0, 0.25, 0.5, 0.75, 1].map((t) => {
                    const val = stats.min + t * (stats.max - stats.min);
                    return (
                      <div key={t} className="legend-tick">
                        <div className="tick-mark" />
                        <span>{val.toFixed(1)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="legend-extremes">
                <span style={{ color: legendColors[0] }}>Low</span>
                <span style={{ color: legendColors[legendColors.length - 1] }}>High</span>
              </div>
              {def.key === 'LULC_Derived' && (
                <div className="lulc-legend">
                  {[
                    { label: 'Vegetation', color: '#006400', val: 0 },
                    { label: 'Built-up', color: '#808080', val: 1 },
                    { label: 'Water', color: '#0000CD', val: 2 },
                    { label: 'Bare/Mixed', color: '#D3D3D3', val: 3 },
                  ].map((cls) => (
                    <div key={cls.val} className="lulc-class">
                      <div style={{ width: 10, height: 10, background: cls.color, borderRadius: 2, flexShrink: 0 }} />
                      <span>{cls.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dataset Stats */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('dataset')}>
            <span>Layer Statistics</span>
            <span>{expandedSection === 'dataset' ? '▾' : '▸'}</span>
          </div>
          {expandedSection === 'dataset' && (
            <div className="stats-list">
              <div className="stat-row">
                <span>Total Pixels</span>
                <span className="stat-val">{config?.total_pixels?.toLocaleString() ?? '—'}</span>
              </div>
              <div className="stat-row">
                <span>Hotspots</span>
                <span className="stat-val heat">{config?.hotspots?.toLocaleString() ?? '—'}</span>
              </div>
              <div className="stat-row">
                <span>Model</span>
                <span className="stat-val accent">{config?.model_name ?? '—'}</span>
              </div>
              <div className="stat-row">
                <span>Features Used</span>
                <span className="stat-val">{config?.n_features ?? '—'}</span>
              </div>
              {stats && (
                <>
                  <div className="stat-divider" />
                  <div className="stat-row">
                    <span>{def?.name} Min</span>
                    <span className="stat-val">{stats.min.toFixed(3)}</span>
                  </div>
                  <div className="stat-row">
                    <span>{def?.name} Mean</span>
                    <span className="stat-val">{stats.mean.toFixed(3)}</span>
                  </div>
                  <div className="stat-row">
                    <span>{def?.name} Max</span>
                    <span className="stat-val">{stats.max.toFixed(3)}</span>
                  </div>
                  <div className="stat-row">
                    <span>Std Dev</span>
                    <span className="stat-val">{stats.std.toFixed(3)}</span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* View Mode + Opacity */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('controls')}>
            <span>Display Controls</span>
            <span>{expandedSection === 'controls' ? '▾' : '▸'}</span>
          </div>
          {expandedSection === 'controls' && (
            <div className="stats-list">
              {/* Heatmap / Grid toggle */}
              <div className="stat-row" style={{ flexDirection: 'column', gap: 6, alignItems: 'stretch' }}>
                <span style={{ fontSize: 10, opacity: 0.7 }}>Render Mode</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => { if (gridView) toggleGridView(); }}
                    style={{
                      flex: 1, padding: '5px 0', fontSize: 10, borderRadius: 6, cursor: 'pointer',
                      background: !gridView ? 'var(--accent)' : 'var(--surface-2)',
                      color: !gridView ? '#000' : 'var(--text-2)',
                      border: `1px solid ${!gridView ? 'var(--accent)' : 'var(--border)'}`,
                      fontWeight: !gridView ? 700 : 400,
                    }}
                  >
                    🌡 Heatmap
                  </button>
                  <button
                    onClick={() => { if (!gridView) toggleGridView(); }}
                    style={{
                      flex: 1, padding: '5px 0', fontSize: 10, borderRadius: 6, cursor: 'pointer',
                      background: gridView ? 'var(--accent)' : 'var(--surface-2)',
                      color: gridView ? '#000' : 'var(--text-2)',
                      border: `1px solid ${gridView ? 'var(--accent)' : 'var(--border)'}`,
                      fontWeight: gridView ? 700 : 400,
                    }}
                  >
                    ⬛ Grid Cells
                  </button>
                </div>
              </div>
              {/* Opacity */}
              <div className="stat-row" style={{ flexDirection: 'column', gap: 4, alignItems: 'stretch' }}>
                <span style={{ fontSize: 10, opacity: 0.7 }}>Opacity: {Math.round(opacity * 100)}%</span>
                <input
                  type="range" min={0.1} max={1} step={0.05}
                  value={opacity}
                  onChange={(e) => setOpacity(+e.target.value)}
                  style={{ width: '100%', accentColor: 'var(--accent)' }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Download */}
        <div className="section">
          <div className="section-title collapsible" onClick={() => toggleSection('download')}>
            <span>Download</span>
            <span>{expandedSection === 'download' ? '▾' : '▸'}</span>
          </div>
          {expandedSection === 'download' && (
            <div className="download-btns">
              <button className="btn-download" onClick={doDownloadLayer}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
                </svg>
                GeoJSON Layer
              </button>
              <button className="btn-download" onClick={doDownloadCSV}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
                </svg>
                CSV Dataset
              </button>
            </div>
          )}
        </div>

      </div>
    </aside>
  );
}
