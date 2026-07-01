import { useConfig, useGridData } from './services/api';
import { useStore } from './store/useStore';
import { useTheme } from './hooks/useTheme';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { MapView } from './components/MapView';
import { PixelDetail } from './components/PixelDetail';
import { Simulator } from './components/Simulator';

export default function App() {
  const { darkMode } = useTheme();
  const { isLoading: cfgLoading, isError: cfgError } = useConfig();
  const { isLoading: gridLoading } = useGridData();

  const loading = cfgLoading || gridLoading;

  return (
    <div className="app" data-theme={darkMode ? 'dark' : 'light'}>
      <Header />
      <MapView />
      <Sidebar />
      <PixelDetail />
      <Simulator />

      {/* Loading overlay */}
      <div className={`loading-overlay ${loading ? '' : 'hidden'}`}>
        <div className="loading-content">
          <div className="loading-logo">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="#ef4444" opacity=".9"/>
              <circle cx="12" cy="9" r="2.5" fill="white"/>
            </svg>
          </div>
          <div className="spinner" />
          <div className="loader-title">Urban Heat AI</div>
          <div className="loader-text">
            {cfgError
              ? '⚠️ Cannot reach API — is the backend running?'
              : 'Loading GIS data & AI models...'}
          </div>
          {!cfgError && (
            <div className="loader-steps">
              <span className={cfgLoading ? 'step-active' : 'step-done'}>
                {cfgLoading ? '⟳' : '✓'} Configuration
              </span>
              <span className={gridLoading ? 'step-active' : cfgLoading ? 'step-pending' : 'step-done'}>
                {gridLoading ? '⟳' : cfgLoading ? '○' : '✓'} Grid data
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
