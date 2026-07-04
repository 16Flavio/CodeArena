import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import { registerUser, loginUser, getMe } from '../api';
import { Zap, Eye, EyeOff, Sun, Moon } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import PasswordStrength from '../components/PasswordStrength';
import { extractErrorMessage } from '../utils/apiError';

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
      toast.error(extractErrorMessage(err, t('auth.registerFailed')));
    } finally {
      setLoading(false);
    }
  };

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
      <div className="card p-8 w-full max-w-md animate-fade-in">
        <h2 className="text-2xl font-bold text-zinc-900 text-center mb-2 dark:text-white">
          {t('auth.registerTitle')}
        </h2>
        <p className="text-zinc-500 text-center mb-8 dark:text-zinc-400">
          {t('auth.registerSubtitle')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
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
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
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
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
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
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 transition-colors dark:text-zinc-500 dark:hover:text-zinc-300"
                aria-label={showPw ? t('auth.hidePassword') : t('auth.showPassword')}
              >
                {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <PasswordStrength password={form.password} />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
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

        <p className="text-center text-zinc-500 text-sm mt-6 dark:text-zinc-500">
          {t('auth.haveAccount')}{' '}
          <Link to="/login" className="text-accent-600 hover:text-accent-500 font-medium dark:text-accent-400 dark:hover:text-accent-300">
            {t('auth.signIn')}
          </Link>
        </p>
      </div>
      </main>
    </div>
  );
}
