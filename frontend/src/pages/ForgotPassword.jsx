import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../ThemeContext';
import { forgotPassword } from '../api';
import { Zap, Mail, CheckCircle, ArrowLeft, Sun, Moon } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../utils/apiError';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword({ email });
      setSent(true);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('auth.somethingWentWrong')));
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
        {sent ? (
          <div className="text-center">
            <div className="w-14 h-14 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center mx-auto mb-5">
              <CheckCircle className="w-7 h-7 text-emerald-500 dark:text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-zinc-900 mb-3 dark:text-white">{t('auth.checkInbox')}</h2>
            <p className="text-zinc-500 mb-6 leading-relaxed dark:text-zinc-400">
              {t('auth.checkInboxBody', { email })}
            </p>
            <Link to="/login" className="btn-primary w-full inline-block text-center">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('auth.backToSignIn')}
            </Link>
          </div>
        ) : (
          <>
            <h2 className="text-2xl font-bold text-zinc-900 text-center mb-2 dark:text-white">
              {t('auth.forgotTitle')}
            </h2>
            <p className="text-zinc-500 text-center mb-8 dark:text-zinc-400">
              {t('auth.forgotSubtitle')}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('auth.email')}
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none dark:text-zinc-500" />
                  <input
                    type="email"
                    className="input-field pl-10"
                    placeholder="vous@exemple.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {t('auth.forgotSending')}
                  </span>
                ) : (
                  t('auth.forgotButton')
                )}
              </button>
            </form>

            <p className="text-center text-zinc-500 text-sm mt-6 dark:text-zinc-500">
              <Link to="/login" className="text-accent-600 hover:text-accent-500 font-medium dark:text-accent-400 dark:hover:text-accent-300">
                <ArrowLeft className="w-3.5 h-3.5 mr-1 inline" />
                {t('auth.backToSignIn')}
              </Link>
            </p>
          </>
        )}
      </div>
      </main>
    </div>
  );
}
