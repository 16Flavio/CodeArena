import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './AuthContext';
import { ThemeProvider, useTheme } from './ThemeContext';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { ConfirmProvider } from './components/Confirm';
import './i18n';
import './index.css';

function ThemedToaster() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: isLight ? '#ffffff' : '#1e293b',
          color: isLight ? '#0f172a' : '#e2e8f0',
          border: `1px solid ${isLight ? '#e2e8f0' : '#334155'}`,
          borderRadius: '12px',
        },
        success: {
          iconTheme: {
            primary: '#22c55e',
            secondary: isLight ? '#ffffff' : '#1e293b',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444',
            secondary: isLight ? '#ffffff' : '#1e293b',
          },
        },
      }}
    />
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ConfirmProvider>
            <ErrorBoundary>
              <App />
            </ErrorBoundary>
            <ThemedToaster />
          </ConfirmProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
);
