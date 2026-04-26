import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Zap, CheckCircle, XCircle, ArrowLeft } from 'lucide-react';
import { verifyEmail } from '../api';

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
  const { t } = useTranslation();

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
          message: err.response?.data?.detail || t('verifyEmail.failed'),
        }),
      );
  }, [token, t]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-slate-950">
      <div className="glass-card p-8 w-full max-w-md text-center animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-2xl font-bold gradient-text">CodeArena</span>
        </div>
        {state.loading ? (
          <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto" />
        ) : state.ok ? (
          <>
            <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4 dark:text-emerald-400" />
            <h2 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">{t('verifyEmail.titleOk')}</h2>
            <p className="text-slate-500 mb-6 dark:text-gray-400">{state.message}</p>
            <Link to="/login" className="btn-primary inline-block">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('verifyEmail.backToLogin')}
            </Link>
          </>
        ) : (
          <>
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4 dark:text-red-400" />
            <h2 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">{t('verifyEmail.titleFailed')}</h2>
            <p className="text-slate-500 mb-6 dark:text-gray-400">{state.message}</p>
            <Link to="/login" className="btn-primary inline-block">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('verifyEmail.backToLogin')}
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
