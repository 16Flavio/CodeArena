import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, BookOpen, CheckCircle2, ChevronRight, Code2 } from 'lucide-react';
import { learnListSections, learnListLessons } from '../api';
import PageHeader from '../components/PageHeader';

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
      <div className="animate-fade-in">
        <Link
          to="/learn"
          className="text-sm font-medium text-accent-600 hover:text-accent-500 dark:text-accent-400 dark:hover:text-accent-300 inline-flex items-center gap-1.5 mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          {t('learn.backToSections')}
        </Link>
        <PageHeader
          eyebrow={t('nav.learn')}
          title={tr(currentSection, 'title')}
          description={tr(currentSection, 'description') || undefined}
        />

        {lessons.length === 0 ? (
          <div className="card p-10 text-center">
            <BookOpen className="w-10 h-10 text-zinc-300 mx-auto mb-3 dark:text-zinc-600" />
            <p className="text-zinc-500 dark:text-zinc-400">{t('learn.noLessons')}</p>
          </div>
        ) : (
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              {t('learn.lessonCount', { count: lessons.length })}
            </h2>
            <div className="card divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {lessons.map((l, idx) => (
                <Link
                  key={l.id}
                  to={`/learn/lessons/${l.id}`}
                  className="px-5 py-3.5 flex items-center gap-4 group hover:bg-zinc-50 transition-colors dark:hover:bg-zinc-800/40"
                >
                  <span className="w-9 h-9 rounded-full border border-zinc-200 text-zinc-500 dark:border-zinc-700 dark:text-zinc-400 flex items-center justify-center font-mono tabular-nums text-sm font-bold shrink-0">
                    {idx + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-zinc-900 truncate group-hover:text-accent-600 dark:text-zinc-100 dark:group-hover:text-accent-300">
                        {tr(l, 'title')}
                      </span>
                      {l.has_exercise && (
                        <Code2 className="w-3.5 h-3.5 text-amber-500 shrink-0" title={t('learn.hasExercise')} />
                      )}
                    </div>
                  </div>
                  {l.progress_status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                  ) : l.progress_status === 'started' ? (
                    <span className="text-xs font-medium text-accent-600 dark:text-accent-400 shrink-0">{t('learn.inProgress')}</span>
                  ) : null}
                  <ChevronRight className="w-5 h-5 text-zinc-300 group-hover:text-accent-500 transition-colors shrink-0 dark:text-zinc-600" />
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    );
  }

  // Sections grid (entry page).
  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={t('nav.learn')}
        title={t('learn.title')}
        description={t('learn.subtitle')}
      />

      {sections.length === 0 ? (
        <div className="card p-10 text-center">
          <BookOpen className="w-10 h-10 text-zinc-300 mx-auto mb-3 dark:text-zinc-600" />
          <p className="text-zinc-500 dark:text-zinc-400">{t('learn.noSections')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.map((s, idx) => {
            const pct = s.lesson_count ? Math.round((s.completed_count / s.lesson_count) * 100) : 0;
            return (
              <Link
                key={s.id}
                to={`/learn/sections/${s.slug}`}
                className="card-hover p-5 group flex flex-col"
              >
                <p className="text-[11px] font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 mb-1.5 font-mono tabular-nums">
                  {String(idx + 1).padStart(2, '0')}
                </p>
                <h2 className="text-lg font-semibold tracking-tight text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                  {tr(s, 'title')}
                </h2>
                {tr(s, 'description') && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2">
                    {tr(s, 'description')}
                  </p>
                )}
                <div className="mt-auto pt-4">
                  <div className="flex items-center justify-between text-xs text-zinc-400 dark:text-zinc-500">
                    <span>{t('learn.lessonCount', { count: s.lesson_count })}</span>
                    <span className="font-mono tabular-nums">
                      {t('learn.completedCount', { done: s.completed_count, total: s.lesson_count })}
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-500 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
