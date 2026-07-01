import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import 'maplibre-gl/dist/maplibre-gl.css';
import './styles/globals.css';

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 2, refetchOnWindowFocus: false } },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
