import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, CheckCircle2, XCircle, Loader2, Code2 } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import { learnGetExercise, learnRunExercise } from '../../../api';
import LessonMarkdown from '../LessonMarkdown';
import { extractErrorMessage } from '../../../utils/apiError';

/**
 * `:::exercise{id="42"}`
 *
 * Renders an inline coding exercise: prompt + CodeMirror editor +
 * Run button + per-testcase verdict pane. Talks to the lesson
 * exercise endpoints which compile + run the user's code through
 * the same sandbox the contest pipeline uses.
 *
 * Hidden test cases (admin-marked ``is_sample=False``) appear as
 * "Test caché #N - réussi/raté" without revealing input/expected.
 */
export default function Exercise({ id }) {
  const { t, i18n } = useTranslation();
  const lng = (i18n.resolvedLanguage || 'fr').slice(0, 2);

  const [exercise, setExercise] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [code, setCode] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await learnGetExercise(id);
        if (cancelled) return;
        setExercise(r.data);
        setCode(r.data?.starter_code || '');
      } catch (err) {
        if (!cancelled) {
          setLoadError(extractErrorMessage(err, t('learn.widget.exercise.loadFailed')));
        }
      }
    })();
    return () => { cancelled = true; };
  }, [id, t]);

  const handleRun = async () => {
    if (!exercise) return;
    setRunning(true);
    setResult(null);
    try {
      const r = await learnRunExercise(id, code, exercise.language);
      setResult(r.data);
    } catch (err) {
      setResult({
        all_passed: false,
        compile_output: '',
        results: [],
        _error: extractErrorMessage(err, t('learn.widget.exercise.runFailed')),
      });
    } finally {
      setRunning(false);
    }
  };

  // CodeMirror language extension. Default to Python; could branch on
  // exercise.language for C/C++/Java but the syntax highlight isn't
  // critical - the bigger win is the editor UX (line numbers, brace
  // matching).
  const cmExtensions = useMemo(() => [python()], []);

  if (!id) {
    return (
      <div className="my-4 p-3 rounded-lg border border-red-300 bg-red-50 text-sm text-red-700 dark:bg-red-950/30 dark:border-red-800 dark:text-red-300">
        {t('learn.widget.exercise.invalid')}
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="my-4 p-3 rounded-lg border border-red-300 bg-red-50 text-sm text-red-700 dark:bg-red-950/30 dark:border-red-800 dark:text-red-300">
        {loadError}
      </div>
    );
  }
  if (!exercise) {
    return (
      <div className="my-6 not-prose p-6 rounded-lg border border-zinc-200 bg-white dark:border-zinc-700/50 dark:bg-zinc-900/50">
        <Loader2 className="w-5 h-5 animate-spin text-accent-500" />
      </div>
    );
  }

  const title = exercise[`title_${lng}`] || exercise.title_fr || t('learn.widget.exercise.defaultTitle');
  const prompt = exercise[`prompt_${lng}`] || exercise.prompt_fr || '';

  return (
    <div className="my-6 not-prose rounded-lg border border-zinc-200 bg-white shadow-sm overflow-hidden dark:border-zinc-700/50 dark:bg-zinc-900/50">
      <div className="px-5 py-3 border-b border-zinc-200 dark:border-zinc-700/50 flex items-center gap-2">
        <Code2 className="w-4 h-4 text-accent-500" />
        <span className="font-semibold text-zinc-900 dark:text-white">{title}</span>
        <span className="text-xs text-zinc-400 dark:text-zinc-500 ml-auto">
          {exercise.language} · {exercise.time_limit_ms} ms
        </span>
      </div>

      {prompt && (
        <div className="px-5 py-3 border-b border-zinc-200 text-sm dark:border-zinc-700/50">
          <LessonMarkdown>{prompt}</LessonMarkdown>
        </div>
      )}

      {exercise.sample_test_cases?.length > 0 && (
        <div className="px-5 py-3 border-b border-zinc-200 dark:border-zinc-700/50">
          <div className="text-xs uppercase tracking-wide font-semibold text-zinc-500 dark:text-zinc-400 mb-2">
            {t('learn.widget.exercise.samples')}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {exercise.sample_test_cases.map((tc, i) => (
              <div key={i} className="text-xs">
                <div className="font-mono text-zinc-500 dark:text-zinc-500 mb-1">
                  {t('learn.widget.exercise.input')} #{i + 1}
                </div>
                <pre className="bg-zinc-50 dark:bg-zinc-900 rounded p-2 overflow-x-auto text-zinc-700 dark:text-zinc-300">{tc.input || '(empty)'}</pre>
                <div className="font-mono text-zinc-500 dark:text-zinc-500 mt-2 mb-1">
                  {t('learn.widget.exercise.expected')}
                </div>
                <pre className="bg-zinc-50 dark:bg-zinc-900 rounded p-2 overflow-x-auto text-zinc-700 dark:text-zinc-300">{tc.expected || '(empty)'}</pre>
              </div>
            ))}
          </div>
        </div>
      )}

      <CodeMirror
        value={code}
        height="280px"
        theme={oneDark}
        extensions={cmExtensions}
        onChange={(v) => setCode(v)}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLine: true,
          foldGutter: true,
          indentOnInput: true,
          tabSize: 4,
        }}
      />

      <div className="px-5 py-3 border-t border-zinc-200 dark:border-zinc-700/50 flex items-center gap-3">
        <button
          onClick={handleRun}
          disabled={running}
          className="btn-primary inline-flex items-center gap-2 disabled:opacity-60"
        >
          {running
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <Play className="w-4 h-4" />}
          {running ? t('learn.widget.exercise.running') : t('learn.widget.exercise.run')}
        </button>
        {exercise.hidden_count > 0 && (
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {t('learn.widget.exercise.hiddenCount', { count: exercise.hidden_count })}
          </span>
        )}
        {result && (
          <span className={`ml-auto inline-flex items-center gap-1 text-sm font-medium ${
            result.all_passed
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-red-600 dark:text-red-400'
          }`}>
            {result.all_passed
              ? <><CheckCircle2 className="w-4 h-4" />{t('learn.widget.exercise.allPassed')}</>
              : <><XCircle className="w-4 h-4" />{t('learn.widget.exercise.someFailed')}</>}
          </span>
        )}
      </div>

      {result && (
        <div className="px-5 py-3 border-t border-zinc-200 dark:border-zinc-700/50 space-y-2">
          {result._error && (
            <div className="text-sm text-red-700 dark:text-red-400">{result._error}</div>
          )}
          {result.compile_output && (
            <details className="text-xs">
              <summary className="cursor-pointer text-zinc-500 dark:text-zinc-400">
                {t('learn.widget.exercise.compileOutput')}
              </summary>
              <pre className="mt-1 bg-zinc-50 dark:bg-zinc-900 rounded p-2 overflow-x-auto text-zinc-700 dark:text-zinc-300">{result.compile_output}</pre>
            </details>
          )}
          {result.results.map((r, i) => (
            <div key={i} className={`flex items-start gap-2 text-sm rounded p-2 ${
              r.passed
                ? 'bg-emerald-50 dark:bg-emerald-950/20'
                : 'bg-red-50 dark:bg-red-950/20'
            }`}>
              {r.passed
                ? <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                : <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />}
              <div className="flex-1 min-w-0 space-y-1">
                <div className="font-medium text-zinc-700 dark:text-zinc-200">
                  {r.is_sample
                    ? t('learn.widget.exercise.sampleN', { n: i + 1 })
                    : t('learn.widget.exercise.hiddenN', { n: i + 1 })}
                  {r.runtime_ms ? ` · ${r.runtime_ms} ms` : ''}
                </div>
                {r.is_sample && !r.passed && r.actual !== undefined && (
                  <div className="text-xs grid grid-cols-2 gap-2">
                    <div>
                      <div className="text-zinc-500 dark:text-zinc-500 mb-0.5">
                        {t('learn.widget.exercise.expected')}
                      </div>
                      <pre className="bg-white dark:bg-zinc-800 rounded p-1 overflow-x-auto whitespace-pre-wrap break-all">{r.expected}</pre>
                    </div>
                    <div>
                      <div className="text-zinc-500 dark:text-zinc-500 mb-0.5">
                        {t('learn.widget.exercise.actual')}
                      </div>
                      <pre className="bg-white dark:bg-zinc-800 rounded p-1 overflow-x-auto whitespace-pre-wrap break-all">{r.actual}</pre>
                    </div>
                  </div>
                )}
                {r.error && (
                  <pre className="text-xs text-red-700 dark:text-red-400 bg-white dark:bg-zinc-800 rounded p-1 overflow-x-auto whitespace-pre-wrap break-all">{r.error}</pre>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
