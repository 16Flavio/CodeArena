import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import { loginUser, getMe, totpLoginVerify } from '../api';
import { Zap, Eye, EyeOff, Sun, Moon, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { extractErrorMessage } from '../utils/apiError';

export default function Login() {
  const [form, setForm] = useState({ username: '', password: '', remember_me: false });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  // Two-step state: when 2FA is enabled, /login returns a challenge
  // and we swap the password form for a code form.
  const [challenge, setChallenge] = useState(null); // { token } or null
  const [code, setCode] = useState('');
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  const finalize = async (accessToken) => {
    login(accessToken, null, { remember: !!form.remember_me });
    const { data: user } = await getMe();
    login(accessToken, user, { remember: !!form.remember_me });
    toast.success(t('auth.signedInAs', { username: user.username }));
    navigate('/dashboard');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await loginUser(form);
      await finalize(data.access_token);
    } catch (err) {
      // 2FA enabled → backend returned 401 with code TOTP_REQUIRED + a
      // challenge_token in params. Pivot to the code-input form.
      const detail = err?.response?.data?.detail;
      if (detail && typeof detail === 'object' && detail.code === 'TOTP_REQUIRED') {
        setChallenge({ token: detail.params?.challenge_token });
        setCode('');
      } else {
        toast.error(extractErrorMessage(err, t('auth.loginFailed')));
      }
    } finally {
      setLoading(false);
    }
  };

  const handle2faSubmit = async (e) => {
    e.preventDefault();
    if (!challenge?.token) return;
    setLoading(true);
    try {
      const { data } = await totpLoginVerify({
        challenge_token: challenge.token,
        code: code.trim(),
      });
      await finalize(data.access_token);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('auth.loginFailed')));
      // Clear the code so the user sees the input emptied and can
      // retype — keeps the challenge alive (still valid for ~5 min).
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  const cancelChallenge = () => {
    setChallenge(null);
    setCode('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-gray-50 dark:bg-slate-950">
      <div className="absolute top-4 right-4 flex items-center gap-1">
        <button
          onClick={toggleLng}
          className="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-gray-100 transition-colors text-xs font-semibold uppercase dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800"
          aria-label={t('nav.language')}
        >
          {currentLng}
        </button>
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-gray-100 transition-colors dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800"
          aria-label={t('nav.toggleTheme')}
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </div>

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

        {challenge ? (
          <>
            <div className="flex items-center justify-center gap-2 mb-2">
              <ShieldCheck className="w-6 h-6 text-violet-500 dark:text-violet-400" />
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                {t('auth.totp.title')}
              </h2>
            </div>
            <p className="text-slate-500 text-center mb-8 dark:text-gray-400">
              {t('auth.totp.subtitle')}
            </p>
            <form onSubmit={handle2faSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                  {t('auth.totp.codeLabel')}
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  className="input-field text-center text-2xl tracking-[0.5em] font-mono"
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  // Allow recovery codes too — those are 20 hex chars,
                  // longer than the 6-digit TOTP. No maxLength gate.
                  required
                  autoFocus
                />
                <p className="text-xs text-slate-400 mt-2 dark:text-gray-500">
                  {t('auth.totp.recoveryHint')}
                </p>
              </div>
              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? t('auth.signingIn') : t('auth.totp.submit')}
              </button>
              <button
                type="button"
                onClick={cancelChallenge}
                className="w-full text-sm text-slate-500 hover:text-slate-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {t('auth.totp.cancel')}
              </button>
            </form>
          </>
        ) : (
          <>
        <h2 className="text-2xl font-bold text-slate-900 text-center mb-2 dark:text-white">
          {t('auth.welcomeBack')}
        </h2>
        <p className="text-slate-500 text-center mb-8 dark:text-gray-400">
          {t('auth.signIn')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.username')}
            </label>
            <input
              type="text"
              className="input-field"
              placeholder={t('auth.usernamePlaceholder')}
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-slate-700 dark:text-gray-300">
                {t('auth.password')}
              </label>
              <Link
                to="/forgot-password"
                className="text-xs text-violet-600 hover:text-violet-500 font-medium dark:text-violet-400 dark:hover:text-violet-300"
              >
                {t('auth.forgotPassword')}
              </Link>
            </div>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input-field pr-12"
                placeholder={t('auth.passwordPlaceholder')}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
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
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.remember_me}
              onChange={(e) => setForm({ ...form, remember_me: e.target.checked })}
            />
            {t('auth.rememberMe')}
          </label>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t('auth.signingIn')}
              </span>
            ) : (
              t('auth.signIn')
            )}
          </button>
        </form>

        <p className="text-center text-slate-500 text-sm mt-6 dark:text-gray-500">
          {t('auth.noAccount')}{' '}
          <Link to="/register" className="text-violet-600 hover:text-violet-500 font-medium dark:text-violet-400 dark:hover:text-violet-300">
            {t('auth.createAccount')}
          </Link>
        </p>
          </>
        )}
      </div>
    </div>
  );
}
