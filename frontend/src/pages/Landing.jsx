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
    <div className="min-h-screen flex flex-col bg-gray-50 text-slate-900 dark:bg-slate-950 dark:text-gray-100">
      <div className="absolute top-4 right-4 flex items-center gap-1 z-10">
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

      <main className="relative flex-1 flex items-center justify-center px-4">
        <div className="glass-card p-10 w-full max-w-md text-center animate-fade-in">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-3xl font-bold gradient-text">CodeArena</span>
          </div>

          <h1 className="text-2xl font-bold text-slate-900 mb-2 dark:text-white">
            {t('landing.welcome')}
          </h1>
          <p className="text-slate-500 mb-8 dark:text-gray-400">
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

      <footer className="relative py-4 text-center text-xs text-slate-400 dark:text-gray-600">
        {t('landing.footer')}
      </footer>
    </div>
  );
}
