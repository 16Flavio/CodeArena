import { useState, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resetPassword } from '../api';
import { Zap, Eye, EyeOff, AlertCircle, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import PasswordStrength from '../components/PasswordStrength';
import { extractErrorMessage } from '../utils/apiError';

// Read the token from EITHER the URL fragment (preferred — never sent
// to the server, never logged by the reverse proxy, never leaked via
// Referer) OR the legacy ``?token=`` query string (for emails minted by
// older releases that haven't expired yet). Fragment wins when both
// are present.
function readResetToken(searchParams) {
  const hash = (typeof window !== 'undefined' ? window.location.hash : '') || '';
  // Strip leading "#" and parse as a URLSearchParams-style fragment.
  const fragment = hash.startsWith('#') ? hash.slice(1) : hash;
  const fromHash = new URLSearchParams(fragment).get('token');
  if (fromHash) return fromHash;
  return searchParams.get('token') || '';
}

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = useMemo(() => readResetToken(params), [params]);
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error(t('auth.passwordsMismatch'));
      return;
    }
    if (form.password.length < 4) {
      toast.error(t('auth.passwordTooShort'));
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ token, new_password: form.password });
      toast.success(t('auth.passwordUpdated'));
      navigate('/login');
    } catch (err) {
      toast.error(extractErrorMessage(err, t('auth.resetFailed')));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-slate-950">
        <div className="glass-card p-8 w-full max-w-md text-center animate-fade-in">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4 dark:text-amber-400" />
          <h2 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">{t('auth.missingResetToken')}</h2>
          <p className="text-slate-500 mb-6 dark:text-gray-400">
            {t('auth.missingResetBody')}
          </p>
          <Link to="/forgot-password" className="btn-primary inline-block">
            {t('auth.requestNewLink')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-gray-50 dark:bg-slate-950">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-violet-500/10 rounded-full blur-[128px] dark:bg-violet-600/15" />
        <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-indigo-500/10 rounded-full blur-[128px] dark:bg-indigo-600/10" />
      </div>

      <div className="relative glass-card p-8 w-full max-w-md animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-2xl font-bold gradient-text">CodeArena</span>
        </div>

        <h2 className="text-2xl font-bold text-slate-900 text-center mb-2 dark:text-white">
          {t('auth.setNewPassword')}
        </h2>
        <p className="text-slate-500 text-center mb-8 dark:text-gray-400">
          {t('auth.setNewPasswordSubtitle')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.newPassword')}
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input-field pr-12"
                placeholder={t('auth.newPasswordPlaceholder')}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors dark:text-gray-500 dark:hover:text-gray-300"
                aria-label={showPw ? t('auth.hidePassword') : t('auth.showPassword')}
              >
                {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <PasswordStrength password={form.password} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.confirmNewPassword')}
            </label>
            <input
              type="password"
              className="input-field"
              placeholder={t('auth.confirmNewPasswordPlaceholder')}
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              autoComplete="new-password"
              required
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t('auth.updatingPassword')}
              </span>
            ) : (
              t('auth.updatePassword')
            )}
          </button>
        </form>

        <p className="text-center text-slate-500 text-sm mt-6 dark:text-gray-500">
          <Link to="/login" className="text-violet-600 hover:text-violet-500 font-medium dark:text-violet-400 dark:hover:text-violet-300">
            <ArrowLeft className="w-3.5 h-3.5 mr-1 inline" />
            {t('auth.backToSignIn')}
          </Link>
        </p>
      </div>
    </div>
  );
}
