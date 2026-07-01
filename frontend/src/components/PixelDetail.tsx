import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { usePixelDetail } from '../services/api';
import { HEAT_COLORS } from '../maps/layerConfig';

const PRIORITY_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#f59e0b',
  Low: '#10b981',
};

const FEASIBILITY_COLORS: Record<string, string> = {
  High: '#10b981',
  Medium: '#f59e0b',
  Low: '#ef4444',
};

function ShapBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.min(Math.abs(value) / Math.abs(max) * 100, 100);
  const isPositive = value >= 0;
  return (
    <div className="shap-row">
      <span className="shap-label">{label.replace(/_/g, ' ')}</span>
      <div className="shap-bar-wrap">
        <div
          className={`shap-bar ${isPositive ? 'shap-heat' : 'shap-cool'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`shap-val ${isPositive ? 'heat-txt' : 'cool-txt'}`}>
        {isPositive ? '+' : ''}{(value as number).toFixed(1)}%
      </span>
    </div>
  );
}

function DetailRow({ label, value, color, mono = true }: {
  label: string; value: string; color?: string; mono?: boolean
}) {
  return (
    <div className="detail-row">
      <span className="label">{label}</span>
      <span className="value" style={{ ...( mono ? {} : {}), color: color ?? 'var(--txt)' }}>
        {value}
      </span>
    </div>
  );
}

export function PixelDetail() {
  const { selectedPixelId, detailOpen, setDetailOpen, setSelectedPixelId } = useStore();
  const { data, isLoading, isError } = usePixelDetail(selectedPixelId);
  const [tab, setTab] = useState<'info' | 'shap' | 'drivers' | 'features'>('info');
  const [scoreAnimated, setScoreAnimated] = useState(0);

  // Animate score number
  useEffect(() => {
    if (!data) { setScoreAnimated(0); return; }
    let frame: number;
    const target = data.heat_score;
    const start = Date.now();
    const duration = 800;
    const animate = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setScoreAnimated(target * eased);
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [data?.heat_score]);

  const close = () => { setDetailOpen(false); setSelectedPixelId(null); };

  const cls = (data?.heat_class ?? 'unknown').toLowerCase();
  const heatColor = HEAT_COLORS[data?.heat_class ?? ''] ?? '#94a3b8';
  const shapEntries = data
    ? Object.entries(data.contributions).sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number)).slice(0, 10)
    : [];
  const maxShap = shapEntries.length ? Math.max(...shapEntries.map(([, v]) => Math.abs(v as number))) : 1;

  return (
    <aside className={`panel detail-panel ${detailOpen ? '' : 'closed'}`}>
      <div className="panel-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
          </svg>
          AI Results Panel
        </div>
        <button className="close-x" onClick={close}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <div className="panel-body">
        {isLoading && (
          <div className="detail-loading">
            <div className="detail-spinner" />
            <span>Loading AI analysis...</span>
          </div>
        )}
        {isError && (
          <div className="detail-error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>Failed to load pixel data</span>
          </div>
        )}

        {data && (
          <>
            {/* Score Card */}
            <div className="score-card" style={{ borderColor: heatColor + '40', background: heatColor + '0a' }}>
              <div className="score-main">
                <div className="score-number" style={{ color: heatColor }}>
                  {scoreAnimated.toFixed(1)}
                </div>
                <div className="score-meta">
                  <span className={`heat-badge badge-${cls}`}>{data.heat_class}</span>
                  <span className="score-label">Heat Score</span>
                </div>
              </div>
              <div className="score-gauge">
                <svg width="70" height="70" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="8"/>
                  <circle
                    cx="50" cy="50" r="40" fill="none"
                    stroke={heatColor} strokeWidth="8"
                    strokeDasharray={`${(data.heat_score / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                    style={{ transition: 'stroke-dasharray 1s ease' }}
                  />
                  <text x="50" y="55" textAnchor="middle" fill={heatColor} fontSize="16" fontWeight="bold">
                    {data.heat_score.toFixed(0)}
                  </text>
                </svg>
              </div>
            </div>

            {/* Tabs */}
            <div className="detail-tabs">
              {(['info', 'shap', 'drivers', 'features'] as const).map((t) => (
                <button
                  key={t}
                  className={`detail-tab ${tab === t ? 'active' : ''}`}
                  onClick={() => setTab(t)}
                >
                  {t === 'info' && '📍 Info'}
                  {t === 'shap' && '📊 SHAP'}
                  {t === 'drivers' && '🔥 Drivers'}
                  {t === 'features' && '📋 Features'}
                </button>
              ))}
            </div>

            {/* Tab: Info */}
            {tab === 'info' && (
              <div className="tab-content">
                <div className="detail-section">
                  <div className="detail-title">📍 Location & Identity</div>
                  <DetailRow label="Pixel ID" value={`#${data.pixel_id}`} />
                  <DetailRow label="Latitude" value={`${data.latitude.toFixed(5)}°N`} />
                  <DetailRow label="Longitude" value={`${data.longitude.toFixed(5)}°E`} />
                </div>

                <div className="detail-section">
                  <div className="detail-title">🌡️ Thermal Analysis</div>
                  <DetailRow label="Heat Score" value={data.heat_score.toFixed(1)} color={heatColor} />
                  <DetailRow label="Heat Category" value={data.heat_class} color={heatColor} />
                  <DetailRow label="LST" value={`${data.lst.toFixed(1)} °C`} />
                  <DetailRow label="Air Temperature" value={`${data.air_temp.toFixed(1)} °C`} />
                </div>

                <div className="detail-section">
                  <div className="detail-title">🤖 AI Prediction</div>
                  <DetailRow label="AI Prediction" value={`${data.heat_score.toFixed(2)} / 100`} color="var(--accent)" />
                  <DetailRow label="Confidence" value={`${(data.confidence * 100).toFixed(0)}%`} color="var(--green)" />
                  <div className="confidence-bar-wrap">
                    <div className="confidence-bar" style={{ width: `${data.confidence * 100}%` }} />
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-title">⚡ Priority & Feasibility</div>
                  <DetailRow
                    label="Priority"
                    value={data.priority}
                    color={PRIORITY_COLORS[data.priority] ?? 'var(--txt)'}
                  />
                  <DetailRow
                    label="Feasibility"
                    value={(data as any).feasibility ?? 'Medium'}
                    color={FEASIBILITY_COLORS[(data as any).feasibility ?? 'Medium']}
                  />
                </div>

                <div className="detail-section">
                  <div className="detail-title">🌿 Cooling Strategy</div>
                  <div className="rec-text">
                    {data.recommendation.split('|').map((r, i) => (
                      <div key={i} className="rec-item">
                        <span className="rec-dot">•</span>
                        <span>{r.trim()}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="detail-section">
                  <div className="detail-title">📉 Expected Outcomes</div>
                  <DetailRow label="Temp Reduction" value={`-${data.predicted_reduction.toFixed(2)} °C`} color="var(--green)" />
                  <DetailRow label="Cost Estimate" value={`₹${(data.cost_estimate / 100000).toFixed(1)}L`} />
                </div>
              </div>
            )}

            {/* Tab: SHAP */}
            {tab === 'shap' && (
              <div className="tab-content">
                <div className="detail-section">
                  <div className="detail-title">📊 SHAP Feature Importance</div>
                  <div className="shap-legend">
                    <span className="shap-legend-heat">■ Heating contribution</span>
                    <span className="shap-legend-cool">■ Cooling contribution</span>
                  </div>
                  <div className="shap-list">
                    {shapEntries.map(([k, v]) => (
                      <ShapBar key={k} label={k} value={v as number} max={maxShap} />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Drivers */}
            {tab === 'drivers' && (
              <div className="tab-content">
                <div className="detail-section">
                  <div className="detail-title">🔥 Dominant Heat Drivers</div>
                  {data.top_drivers.map((d) => (
                    <div key={d.feature} className="driver-item">
                      <div className="driver-header">
                        <span className="driver-name">{d.feature.replace(/_/g, ' ')}</span>
                        <span className={`driver-pct ${d.direction === 'heating' ? 'heat-txt' : 'cool-txt'}`}>
                          {d.contribution_pct.toFixed(1)}%
                          {d.direction === 'heating' ? ' ↑' : ' ↓'}
                        </span>
                      </div>
                      <div className="driver-bar-track">
                        <div
                          className={`driver-bar ${d.direction === 'heating' ? 'driver-heat' : 'driver-cool'}`}
                          style={{ width: `${Math.min(d.contribution_pct, 100)}%` }}
                        />
                      </div>
                      <div className="driver-val">Value: {d.value?.toFixed(2) ?? '—'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab: Features */}
            {tab === 'features' && (
              <div className="tab-content">
                <div className="detail-section">
                  <div className="detail-title">📋 All Feature Values</div>
                  <div className="features-grid">
                    {Object.entries(data.features).map(([k, v]) => (
                      <div key={k} className="feature-cell">
                        <span className="feature-key">{k.replace(/_/g, ' ')}</span>
                        <span className="feature-val">{(v as number).toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
