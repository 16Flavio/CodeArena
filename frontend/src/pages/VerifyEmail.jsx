import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../ThemeContext';
import { Zap, CheckCircle, XCircle, ArrowLeft, Sun, Moon } from 'lucide-react';
import { verifyEmail } from '../api';
import { extractErrorMessage } from '../utils/apiError';

// Token preferred from the URL fragment (never reaches the server's
// access logs, never leaks via Referer); fall back to the legacy
// ``?token=`` query string for emails minted before the fragment
// switch.
function readVerifyToken(searchParams) {
  const hash = (typeof window !== 'undefined' ? window.location.hash : '') || '';
  const fragment = hash.startsWith('#') ? hash.slice(1) : hash;
  const fromHash = new URLSearchParams(fragment).get('token');
  if (fromHash) return fromHash;
  return searchParams.get('token') || '';
}

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = readVerifyToken(params);
  const [state, setState] = useState({ loading: true, ok: false, message: '' });
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  useEffect(() => {
    if (!token) {
      setState({ loading: false, ok: false, message: t('verifyEmail.missingToken') });
      return;
    }
    verifyEmail(token)
      .then((r) => setState({ loading: false, ok: true, message: r.data?.detail || t('verifyEmail.verified') }))
      .catch((err) =>
        setState({
          loading: false,
          ok: false,
          message: extractErrorMessage(err, t('verifyEmail.failed')),
        }),
      );
  }, [token, t]);

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {/* Top bar - same treatment as the landing page. */}
      <header className="border-b border-zinc-200/80 dark:border-zinc-800/80">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-3" aria-label="CodeArena">
            <span className="w-8 h-8 rounded-full bg-accent-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </span>
            <span className="text-[17px] font-bold tracking-tight">CodeArena</span>
          </Link>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              onClick={toggleLng}
              className="p-2 rounded-full text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors text-xs font-mono font-semibold uppercase dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
              aria-label={t('nav.language')}
            >
              {currentLng}
            </button>
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
              aria-label={t('nav.toggleTheme')}
            >
              {theme === 'dark' ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-12">
      <div className="card p-8 w-full max-w-md text-center animate-fade-in">
        {state.loading ? (
          <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto" />
        ) : state.ok ? (
          <>
            <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4 dark:text-emerald-400" />
            <h2 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('verifyEmail.titleOk')}</h2>
            <p className="text-zinc-500 mb-6 dark:text-zinc-400">{state.message}</p>
            <Link to="/login" className="btn-primary inline-block">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('verifyEmail.backToLogin')}
            </Link>
          </>
        ) : (
          <>
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4 dark:text-red-400" />
            <h2 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('verifyEmail.titleFailed')}</h2>
            <p className="text-zinc-500 mb-6 dark:text-zinc-400">{state.message}</p>
            <Link to="/login" className="btn-primary inline-block">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('verifyEmail.backToLogin')}
            </Link>
          </>
        )}
      </div>
      </main>
    </div>
  );
}
