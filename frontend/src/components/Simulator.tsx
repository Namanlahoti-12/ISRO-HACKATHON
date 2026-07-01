import { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import { useSpatialPredict } from '../services/api';
import type { ScenarioParams, SimView } from '../types';

const SLIDERS: {
  key: keyof ScenarioParams;
  label: string;
  icon: string;
  max: number;
  step: number;
  fmt?: (v: number) => string;
  description: string;
}[] = [
  { key: 'tree_cover_pct',                label: 'Tree Cover',    icon: '🌳', max: 60, step: 1, description: 'Urban forest & parks' },
  { key: 'green_roof_pct',                label: 'Green Roof',    icon: '🌱', max: 50, step: 1, description: 'Vegetated rooftops' },
  { key: 'cool_roof_pct',                 label: 'Cool Roof',     icon: '🏠', max: 80, step: 1, description: 'High-albedo surfaces' },
  { key: 'water_body_pct',                label: 'Water Body',    icon: '💧', max: 30, step: 1, description: 'Lakes, ponds, canals' },
  { key: 'albedo_change',                 label: 'Albedo',        icon: '☀️', max: 30, step: 1, fmt: (v) => (v / 100).toFixed(2), description: 'Surface reflectivity' },
  { key: 'impervious_reduction_pct',      label: 'Imperv. ↓',    icon: '🚧', max: 50, step: 1, description: 'Reduce paved surfaces' },
  { key: 'building_density_reduction_pct', label: 'Bldg Density ↓', icon: '🏢', max: 30, step: 1, description: 'Building density change' },
];

const VIEW_OPTIONS: { value: SimView; label: string; icon: string; desc: string }[] = [
  { value: 'before', label: 'Before', icon: '⬤', desc: 'Baseline heat map' },
  { value: 'after',  label: 'After',  icon: '⬤', desc: 'Post-intervention heat map' },
  { value: 'diff',   label: 'Diff',   icon: '⬤', desc: 'Temperature difference map' },
];

export function Simulator() {
  const { simExpanded, setSimExpanded, simView, setSimView, scenario, setScenarioParam, resetScenario, setSpatialResult } = useStore();
  const mutation = useSpatialPredict();
  const result = useStore((s) => s.spatialResult);
  const requestSeq = useRef(0);

  const totalChange = Object.values(scenario).reduce((s, v) => s + v, 0);
  const hasChanges = totalChange > 0;

  const runScenario = (params: ScenarioParams) => {
    const requestId = ++requestSeq.current;
    mutation.mutate(params, {
      onSuccess: (data) => {
        if (requestId !== requestSeq.current) return;
        setSpatialResult(data);
        useStore.getState().setSimView('after');
      },
    });
  };

  useEffect(() => {
    if (!hasChanges) {
      requestSeq.current += 1;
      setSpatialResult(null);
      useStore.getState().setSimView('before');
      return;
    }

    const timer = window.setTimeout(() => runScenario(scenario), 450);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario, hasChanges, setSpatialResult]);

  const run = () => {
    if (hasChanges) runScenario(scenario);
  };

  const reset = () => {
    requestSeq.current += 1;
    resetScenario();
    setSpatialResult(null);
    mutation.reset();
  };

  const summary = result?.summary;

  return (
    <div className={`simulator ${simExpanded ? 'expanded' : ''}`}>
      {/* Header */}
      <div className="sim-head" onClick={() => setSimExpanded(!simExpanded)}>
        <div className="sim-head-left">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span className="sim-title">Scenario Simulator</span>
          {hasChanges && <span className="sim-modified-badge">{Object.values(scenario).filter(v => v > 0).length} active</span>}
        </div>

        <div className="sim-kpis">
          {summary ? (
            <>
              <span className="kpi kpi-heat">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
                Before: {summary.before_mean.toFixed(1)}
              </span>
              <span className="kpi kpi-cool">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
                After: {summary.after_mean.toFixed(1)}
              </span>
              <span className="kpi kpi-green">
                ↓ {summary.reduction.toFixed(1)} ({summary.reduction_pct}%)
              </span>
            </>
          ) : (
            <span className="sim-hint">Configure parameters below and run simulation</span>
          )}
        </div>

        <svg
          width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ transform: simExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform .2s', flexShrink: 0 }}
        >
          <polyline points="18 15 12 9 6 15"/>
        </svg>
      </div>

      {/* Body */}
      <div className="sim-body">
        {/* Sliders */}
        <div className="sim-controls">
          {SLIDERS.map((s) => {
            const val = scenario[s.key];
            const pct = (val / s.max) * 100;
            return (
              <div className="sim-group" key={s.key}>
                <div className="sim-group-header">
                  <span className="sim-group-icon">{s.icon}</span>
                  <span className="sim-group-label">{s.label}</span>
                  <span className="sv">{s.fmt ? s.fmt(val) : `${val}%`}</span>
                </div>
                <div className="sim-slider-wrap">
                  <input
                    type="range" min={0} max={s.max} step={s.step}
                    value={val}
                    onChange={(e) => setScenarioParam(s.key, +e.target.value)}
                  />
                  <div className="sim-slider-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="sim-group-desc">{s.description}</span>
              </div>
            );
          })}
        </div>

        {/* Actions */}
        <div className="sim-actions">
          {/* View Selector */}
          <div className="sim-view-selector">
            {VIEW_OPTIONS.map((v) => (
              <button
                key={v.value}
                className={`sim-view-btn ${simView === v.value ? 'active' : ''} ${v.value === 'diff' ? 'diff' : ''}`}
                onClick={() => setSimView(v.value)}
                disabled={v.value !== 'before' && !result}
                title={v.desc}
              >
                {v.icon} {v.label}
              </button>
            ))}
          </div>

          {/* Diff Legend */}
          {simView === 'diff' && result && (
            <div className="diff-legend">
              <div className="diff-legend-bar" />
              <div className="diff-legend-labels">
                <span>Cooler</span>
                <span>No change</span>
                <span>Hotter</span>
              </div>
            </div>
          )}

          {/* Run/Reset */}
          <button
            className={`btn-predict ${mutation.isPending ? 'loading' : ''}`}
            onClick={run}
            disabled={mutation.isPending || !hasChanges}
          >
            {mutation.isPending ? (
              <>
                <span className="btn-spinner" />
                Computing...
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Run Simulation
              </>
            )}
          </button>

          <button className="btn-reset" onClick={reset} disabled={mutation.isPending}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.9"/>
            </svg>
            Reset
          </button>

          {/* Result Summary Card */}
          {summary && (
            <div className="sim-result-card">
              <div className="sim-result-title">Simulation Results</div>
              <div className="sim-result-grid">
                <div className="sim-result-item">
                  <span className="sim-result-label">Baseline</span>
                  <span className="sim-result-val heat-txt">{summary.before_mean.toFixed(2)}</span>
                </div>
                <div className="sim-result-item">
                  <span className="sim-result-label">Post-intervention</span>
                  <span className="sim-result-val cool-txt">{summary.after_mean.toFixed(2)}</span>
                </div>
                <div className="sim-result-item">
                  <span className="sim-result-label">Reduction</span>
                  <span className="sim-result-val green-txt">↓ {summary.reduction.toFixed(2)}</span>
                </div>
                <div className="sim-result-item">
                  <span className="sim-result-label">% Change</span>
                  <span className="sim-result-val green-txt">{summary.reduction_pct}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
