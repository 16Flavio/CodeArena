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
          background: isLight ? '#ffffff' : '#18181b',
          color: isLight ? '#18181b' : '#e4e4e7',
          border: `1px solid ${isLight ? '#e4e4e7' : '#334155'}`,
          borderRadius: '12px',
        },
        success: {
          iconTheme: {
            primary: '#22c55e',
            secondary: isLight ? '#ffffff' : '#18181b',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444',
            secondary: isLight ? '#ffffff' : '#18181b',
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
