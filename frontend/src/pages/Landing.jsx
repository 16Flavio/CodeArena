import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import { useTranslation } from 'react-i18next';
import {
  Zap, ArrowRight, Sun, Moon, Trophy, GraduationCap, Medal, CheckCircle2,
} from 'lucide-react';

// Illustrative scoreboard fragment for the hero - real UI vocabulary
// (balloon dots, verdict cells, mono numerals), static content.
function BoardPreview({ t }) {
  const rows = [
    { rank: 1, team: 'les_turing', solved: 5, pen: 287, cells: ['ac', 'ac', 'wa'] },
    { rank: 2, team: 'seg_fault', solved: 4, pen: 312, cells: ['ac', 'wa', 'ac'] },
    { rank: 3, team: 'off_by_one', solved: 4, pen: 355, cells: ['wa', 'ac', 'ac'] },
  ];
  const dots = ['#d9534f', '#f0ad4e', '#5b9bd5'];
  return (
    <div className="card overflow-hidden shadow-xl shadow-zinc-950/5 dark:shadow-black/40" aria-hidden="true">
      <div className="px-5 py-3 flex items-center gap-2.5 border-b border-zinc-100 dark:border-zinc-800/60">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-xs font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
          {t('landing.previewLive')}
        </span>
        <span className="ml-auto font-mono tabular-nums text-sm font-semibold text-zinc-900 dark:text-white">02:14:33</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
            <th className="text-left font-semibold py-2 pl-5 w-8">#</th>
            <th className="text-left font-semibold py-2">{t('landing.previewTeam')}</th>
            {dots.map((c, i) => (
              <th key={c} className="py-2 text-center w-10">
                <span
                  className="inline-block w-5 h-5 rounded-full text-[10px] font-bold leading-5 text-white"
                  style={{ background: c }}
                >
                  {String.fromCharCode(65 + i)}
                </span>
              </th>
            ))}
            <th className="text-right font-semibold py-2 pr-5">{t('landing.previewPen')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.rank} className="border-t border-zinc-100 dark:border-zinc-800/50">
              <td className="py-2.5 pl-5 font-mono tabular-nums font-bold text-zinc-400 dark:text-zinc-500">{r.rank}</td>
              <td className="py-2.5 font-medium text-zinc-900 dark:text-zinc-100">{r.team}</td>
              {r.cells.map((v, i) => (
                <td key={i} className="py-2.5 text-center font-mono text-xs">
                  {v === 'ac'
                    ? <CheckCircle2 className="w-4 h-4 inline text-emerald-500" />
                    : <span className="text-red-500 font-bold">-1</span>}
                </td>
              ))}
              <td className="py-2.5 pr-5 text-right font-mono tabular-nums text-zinc-500 dark:text-zinc-400">{r.pen}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Landing() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  const features = [
    {
      icon: Trophy,
      title: t('landing.featContestsTitle'),
      body: t('landing.featContestsBody'),
    },
    {
      icon: GraduationCap,
      title: t('landing.featLearnTitle'),
      body: t('landing.featLearnBody'),
    },
    {
      icon: Medal,
      title: t('landing.featLeagueTitle'),
      body: t('landing.featLeagueBody'),
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {/* Top bar */}
      <header className="border-b border-zinc-200/80 dark:border-zinc-800/80">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center gap-3">
          <span className="w-8 h-8 rounded-full bg-accent-600 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </span>
          <span className="text-[17px] font-bold tracking-tight">CodeArena</span>
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
            {user ? (
              <Link to="/dashboard" className="btn-primary text-sm ml-2">
                {t('nav.dashboard')}
              </Link>
            ) : (
              <Link to="/login" className="btn-secondary text-sm ml-2">
                {t('auth.signIn')}
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-5 pt-16 lg:pt-24 pb-16 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-accent-600 dark:text-accent-400 mb-4">
              {t('landing.heroEyebrow')}
            </p>
            <h1
              className="text-4xl lg:text-5xl font-bold tracking-tight leading-[1.08]"
              style={{ textWrap: 'balance' }}
            >
              {t('landing.heroTitle')}
            </h1>
            <p className="text-lg text-zinc-500 dark:text-zinc-400 mt-5 max-w-xl">
              {t('landing.heroSub')}
            </p>
            <div className="flex items-center gap-3 mt-8">
              {user ? (
                <Link to="/dashboard" className="btn-primary inline-flex items-center text-base px-6 py-2.5">
                  {t('nav.dashboard')}
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              ) : (
                <>
                  <Link to="/register" className="btn-primary inline-flex items-center text-base px-6 py-2.5">
                    {t('landing.registerCta')}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Link>
                  <Link to="/login" className="btn-secondary inline-flex items-center text-base px-6 py-2.5">
                    {t('auth.signIn')}
                  </Link>
                </>
              )}
            </div>
          </div>
          <BoardPreview t={t} />
        </section>

        {/* Features */}
        <section className="border-t border-zinc-200/80 dark:border-zinc-800/80">
          <div className="max-w-6xl mx-auto px-5 py-16 grid md:grid-cols-3 gap-10">
            {features.map((f) => (
              <div key={f.title}>
                <div className="w-10 h-10 rounded-full bg-accent-100 text-accent-700 flex items-center justify-center mb-4 dark:bg-accent-950 dark:text-accent-300">
                  <f.icon className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-bold tracking-tight mb-2">{f.title}</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-200/80 dark:border-zinc-800/80">
        <div className="max-w-6xl mx-auto px-5 py-6 flex items-center gap-3 text-sm text-zinc-400 dark:text-zinc-500">
          <span className="w-5 h-5 rounded-full bg-accent-600/90 flex items-center justify-center">
            <Zap className="w-3 h-3 text-white" />
          </span>
          <span>{t('landing.footer')}</span>
        </div>
      </footer>
    </div>
  );
}
