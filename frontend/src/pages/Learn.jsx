import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GraduationCap, BookOpen, CheckCircle2, ChevronRight, Code2 } from 'lucide-react';
import { learnListSections, learnListLessons } from '../api';

// Browse view: list sections, drill into a section to see its lessons.
// One page handles both states because the URL ``/learn`` and
// ``/learn/sections/:slug`` share most of the layout.
export default function Learn() {
  const { t, i18n } = useTranslation();
  const { slug } = useParams();
  const lng = (i18n.resolvedLanguage || 'fr').slice(0, 2);
  const [sections, setSections] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const sr = await learnListSections();
        if (!cancelled) setSections(sr.data || []);
        if (slug) {
          const lr = await learnListLessons(slug);
          if (!cancelled) setLessons(lr.data || []);
        } else {
          setLessons([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [slug]);

  const currentSection = slug ? sections.find((s) => s.slug === slug) : null;
  const tr = (obj, field) => obj[`${field}_${lng}`] || obj[`${field}_fr`] || '';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (slug && currentSection) {
    return (
      <div className="space-y-6">
        <div>
          <Link
            to="/learn"
            className="text-sm text-accent-600 hover:text-accent-500 dark:text-accent-400 inline-flex items-center gap-1"
          >
            ← {t('learn.backToSections')}
          </Link>
          <h1 className="text-3xl font-bold mt-3 text-zinc-900 dark:text-white flex items-center gap-3">
            <BookOpen className="w-7 h-7 text-accent-500" />
            {tr(currentSection, 'title')}
          </h1>
          {tr(currentSection, 'description') && (
            <p className="text-zinc-500 dark:text-zinc-400 mt-2">{tr(currentSection, 'description')}</p>
          )}
        </div>

        {lessons.length === 0 ? (
          <div className="card p-8 text-center">
            <p className="text-zinc-500 dark:text-zinc-400">{t('learn.noLessons')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {lessons.map((l, idx) => (
              <Link
                key={l.id}
                to={`/learn/lessons/${l.id}`}
                className="card p-4 flex items-center gap-4 hover:border-accent-300 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-accent-100 text-accent-700 dark:bg-accent-500/20 dark:text-accent-300 flex items-center justify-center font-semibold text-sm">
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-zinc-900 dark:text-white truncate">
                      {tr(l, 'title')}
                    </span>
                    {l.has_exercise && (
                      <Code2 className="w-3.5 h-3.5 text-amber-500" title={t('learn.hasExercise')} />
                    )}
                  </div>
                </div>
                {l.progress_status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : l.progress_status === 'started' ? (
                  <span className="text-xs text-accent-600 dark:text-accent-400">{t('learn.inProgress')}</span>
                ) : null}
                <ChevronRight className="w-5 h-5 text-zinc-300 group-hover:text-accent-500 transition-colors dark:text-zinc-600" />
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Sections grid (entry page).
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
          <GraduationCap className="w-8 h-8 text-accent-500" />
          {t('learn.title')}
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mt-2">{t('learn.subtitle')}</p>
      </div>

      {sections.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-zinc-500 dark:text-zinc-400">{t('learn.noSections')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.map((s) => {
            const pct = s.lesson_count ? Math.round((s.completed_count / s.lesson_count) * 100) : 0;
            return (
              <Link
                key={s.id}
                to={`/learn/sections/${s.slug}`}
                className="card p-5 hover:border-accent-300 transition-colors group"
              >
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">{tr(s, 'title')}</h2>
                {tr(s, 'description') && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2">
                    {tr(s, 'description')}
                  </p>
                )}
                <div className="mt-4 flex items-center justify-between text-xs text-zinc-400 dark:text-zinc-500">
                  <span>{t('learn.lessonCount', { count: s.lesson_count })}</span>
                  <span>{t('learn.completedCount', { done: s.completed_count, total: s.lesson_count })}</span>
                </div>
                <div className="mt-2 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent-500 transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
