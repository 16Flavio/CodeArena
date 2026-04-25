import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import { registerUser, loginUser, getMe } from '../api';
import { Zap, Eye, EyeOff, Sun, Moon } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import PasswordStrength from '../components/PasswordStrength';

export default function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

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
      await registerUser({
        username: form.username,
        email: form.email,
        password: form.password,
      });
      const { data } = await loginUser({
        username: form.username,
        password: form.password,
      });
      // Fresh registration -> don't persist across tab close; the user
      // can tick "Remember me" on the login form later if they want.
      login(data.access_token, null);
      const { data: user } = await getMe();
      login(data.access_token, user);
      toast.success(t('auth.accountCreated'));
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || t('auth.registerFailed'));
    } finally {
      setLoading(false);
    }
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

        <h2 className="text-2xl font-bold text-slate-900 text-center mb-2 dark:text-white">
          {t('auth.registerTitle')}
        </h2>
        <p className="text-slate-500 text-center mb-8 dark:text-gray-400">
          {t('auth.registerSubtitle')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.username')}
            </label>
            <input
              type="text"
              className="input-field"
              placeholder={t('auth.chooseUsername')}
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.email')}
            </label>
            <input
              type="email"
              className="input-field"
              placeholder={t('auth.emailPlaceholder')}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.password')}
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input-field pr-12"
                placeholder={t('auth.createPassword')}
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
            <PasswordStrength password={form.password} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
              {t('auth.confirmPassword')}
            </label>
            <input
              type="password"
              className="input-field"
              placeholder={t('auth.confirmPasswordPlaceholder')}
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              required
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t('auth.creatingAccount')}
              </span>
            ) : (
              t('auth.submitCreate')
            )}
          </button>
        </form>

        <p className="text-center text-slate-500 text-sm mt-6 dark:text-gray-500">
          {t('auth.haveAccount')}{' '}
          <Link to="/login" className="text-violet-600 hover:text-violet-500 font-medium dark:text-violet-400 dark:hover:text-violet-300">
            {t('auth.signIn')}
          </Link>
        </p>
      </div>
    </div>
  );
}
