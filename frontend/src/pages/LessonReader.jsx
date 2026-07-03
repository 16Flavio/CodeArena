import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, ArrowLeft, Code2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { learnGetLesson, learnSetProgress } from '../api';
import LessonMarkdown from '../components/learning/LessonMarkdown';
import { extractErrorMessage } from '../utils/apiError';

export default function LessonReader() {
  const { lessonId } = useParams();
  const { t, i18n } = useTranslation();
  const lng = (i18n.resolvedLanguage || 'fr').slice(0, 2);
  const navigate = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const r = await learnGetLesson(lessonId);
        if (!cancelled) setLesson(r.data);
      } catch (err) {
        if (!cancelled) toast.error(extractErrorMessage(err, t('learn.toastLoadFailed')));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [lessonId, t]);

  const handleComplete = async () => {
    setMarking(true);
    try {
      const r = await learnSetProgress(lessonId, 'completed');
      setLesson(r.data);
      toast.success(t('learn.toastCompleted'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('learn.toastFailed')));
    } finally {
      setMarking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!lesson) {
    return (
      <div className="card p-8 text-center">
        <p className="text-zinc-500 dark:text-zinc-400">{t('learn.lessonNotFound')}</p>
        <button onClick={() => navigate('/learn')} className="btn-primary mt-4">
          <ArrowLeft className="w-4 h-4 mr-2 inline" />
          {t('learn.backToSections')}
        </button>
      </div>
    );
  }

  const title = lesson[`title_${lng}`] || lesson.title_fr;
  const content = lesson[`content_${lng}`] || lesson.content_fr;
  const isCompleted = lesson.progress_status === 'completed';

  return (
    <article className="max-w-4xl mx-auto space-y-6">
      <div>
        <Link
          to="/learn"
          className="text-sm text-accent-600 hover:text-accent-500 dark:text-accent-400 inline-flex items-center gap-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          {t('learn.backToSections')}
        </Link>
        <h1 className="text-3xl font-bold mt-3 text-zinc-900 dark:text-white">{title}</h1>
      </div>

      <LessonMarkdown>{content}</LessonMarkdown>

      {lesson.exercise_problem_id && (
        <div className="card p-5 border-amber-300 dark:border-amber-500/30">
          <h3 className="font-semibold text-zinc-900 dark:text-white flex items-center gap-2 mb-2">
            <Code2 className="w-5 h-5 text-amber-500" />
            {t('learn.exerciseTitle')}
          </h3>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">{t('learn.exerciseHint')}</p>
          {/* The exercise endpoint reuses the existing problem submit
              flow. We point at the problem detail; the user submits
              there and progresses against the lesson by clicking the
              Mark Completed button below. */}
        </div>
      )}

      <div className="flex justify-end pt-4 border-t border-zinc-200 dark:border-zinc-700/50">
        {isCompleted ? (
          <span className="inline-flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-medium">
            <CheckCircle2 className="w-5 h-5" />
            {t('learn.completed')}
          </span>
        ) : (
          <button
            onClick={handleComplete}
            disabled={marking}
            className="btn-primary inline-flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            {marking ? t('learn.saving') : t('learn.markCompleted')}
          </button>
        )}
      </div>
    </article>
  );
}
