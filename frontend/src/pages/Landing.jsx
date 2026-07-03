import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import { useTranslation } from 'react-i18next';
import { Zap, ArrowRight, Sun, Moon } from 'lucide-react';

export default function Landing() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="absolute top-4 right-4 flex items-center gap-1 z-10">
        <button
          onClick={toggleLng}
          className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors text-xs font-semibold uppercase dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800"
          aria-label={t('nav.language')}
        >
          {currentLng}
        </button>
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800"
          aria-label={t('nav.toggleTheme')}
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </div>

      <main className="relative flex-1 flex items-center justify-center px-4">
        <div className="card p-10 w-full max-w-md text-center animate-fade-in">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-accent-600 flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-3xl font-bold text-zinc-900 dark:text-white">CodeArena</span>
          </div>

          <h1 className="text-2xl font-bold text-zinc-900 mb-2 dark:text-white">
            {t('landing.welcome')}
          </h1>
          <p className="text-zinc-500 mb-8 dark:text-zinc-400">
            {t('landing.welcomeSub')}
          </p>

          {user ? (
            <Link to="/dashboard" className="btn-primary w-full inline-flex items-center justify-center">
              {t('nav.dashboard')} <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          ) : (
            <div className="flex flex-col gap-3">
              <Link to="/register" className="btn-primary w-full inline-flex items-center justify-center">
                {t('landing.registerCta')}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
              <Link to="/login" className="btn-secondary w-full text-center">
                {t('auth.signIn')}
              </Link>
            </div>
          )}
        </div>
      </main>

      <footer className="relative py-4 text-center text-xs text-zinc-400 dark:text-zinc-600">
        {t('landing.footer')}
      </footer>
    </div>
  );
}
