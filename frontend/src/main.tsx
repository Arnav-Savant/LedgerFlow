import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: { background: '#1c2128', color: '#e6edf3', border: '1px solid #30363d', fontSize: '0.85rem' },
        success: { iconTheme: { primary: '#3fb950', secondary: '#1c2128' } },
        error: { iconTheme: { primary: '#f85149', secondary: '#1c2128' } },
      }}
    />
  </StrictMode>,
);
