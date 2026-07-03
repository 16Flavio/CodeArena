import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Plus, Trash2, Save, Code2, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  adminLearnListExercises, adminLearnCreateExercise,
  adminLearnUpdateExercise, adminLearnDeleteExercise,
} from '../../api';
import { extractErrorMessage } from '../../utils/apiError';

const DEFAULT_TEST_CASE = { input: '', expected: '', is_sample: true };

const STARTER_BY_LANG = {
  py3:  '# Lis stdin, écris stdout.\nimport sys\ndata = sys.stdin.read()\nprint(data)\n',
  cpp:  '#include <bits/stdc++.h>\nusing namespace std;\nint main() {\n    // your code here\n    return 0;\n}\n',
  c:    '#include <stdio.h>\nint main(void) {\n    /* your code here */\n    return 0;\n}\n',
  java: 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        // your code here\n    }\n}\n',
};

/**
 * Modal that lists exercises attached to a lesson, lets the admin
 * create / edit / delete them, and inserts the corresponding
 * ``:::exercise{id="..."}`` directive into the markdown editor on
 * pick. The CRUD form is on the right; the list of existing
 * exercises is on the left.
 */
export default function ExercisePickerModal({ open, onClose, lessonId, onInsertDirective }) {
  const { t } = useTranslation();
  const [exercises, setExercises] = useState([]);
  const [editing, setEditing] = useState(null);  // { id?, ...data }
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !lessonId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const r = await adminLearnListExercises(lessonId);
        if (!cancelled) setExercises(r.data || []);
      } catch (err) {
        if (!cancelled) toast.error(extractErrorMessage(err, t('exercisePicker.loadFailed')));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, lessonId, t]);

  const refresh = async () => {
    try {
      const r = await adminLearnListExercises(lessonId);
      setExercises(r.data || []);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('exercisePicker.loadFailed')));
    }
  };

  const handleNew = () => {
    setEditing({
      title_fr: '', title_en: '',
      prompt_fr: '', prompt_en: '',
      language: 'py3',
      starter_code: STARTER_BY_LANG.py3,
      test_cases: [{ ...DEFAULT_TEST_CASE }],
      time_limit_ms: 2000,
    });
  };

  const handleSave = async () => {
    if (!editing) return;
    try {
      const payload = {
        title_fr: editing.title_fr, title_en: editing.title_en,
        prompt_fr: editing.prompt_fr, prompt_en: editing.prompt_en,
        language: editing.language,
        starter_code: editing.starter_code,
        test_cases: editing.test_cases.map((c) => ({
          input: c.input || '',
          expected: c.expected || '',
          is_sample: c.is_sample !== false,
        })),
        time_limit_ms: editing.time_limit_ms,
      };
      let saved;
      if (editing.id) {
        const r = await adminLearnUpdateExercise(editing.id, payload);
        saved = r.data;
      } else {
        const r = await adminLearnCreateExercise(lessonId, payload);
        saved = r.data;
      }
      toast.success(t('exercisePicker.saved'));
      setEditing(saved);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('exercisePicker.saveFailed')));
    }
  };

  const handleDelete = async (ex) => {
    if (!window.confirm(t('exercisePicker.confirmDelete'))) return;
    try {
      await adminLearnDeleteExercise(ex.id);
      toast.success(t('exercisePicker.deleted'));
      if (editing?.id === ex.id) setEditing(null);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('exercisePicker.saveFailed')));
    }
  };

  const handleInsert = (ex) => {
    if (!onInsertDirective) return;
    onInsertDirective(`:::exercise{id="${ex.id}"}\n:::`);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-12 px-4 bg-black/50" onClick={onClose}>
      <div className="glass-card max-w-6xl w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700/50">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Code2 className="w-5 h-5 text-amber-500" />
            {t('exercisePicker.title')}
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700/50 text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden grid grid-cols-12 gap-0">
          {/* List */}
          <div className="col-span-4 border-r border-gray-200 dark:border-slate-700/50 overflow-y-auto p-3 space-y-2">
            <button
              onClick={handleNew}
              className="w-full btn-primary text-sm inline-flex items-center justify-center gap-1"
            >
              <Plus className="w-4 h-4" />
              {t('exercisePicker.new')}
            </button>
            {loading && <div className="text-xs text-slate-400">{t('exercisePicker.loading')}</div>}
            {!loading && exercises.length === 0 && (
              <p className="text-xs text-slate-400 dark:text-gray-500 text-center py-4">
                {t('exercisePicker.empty')}
              </p>
            )}
            {exercises.map((ex) => (
              <div
                key={ex.id}
                className={`p-2 rounded cursor-pointer ${
                  editing?.id === ex.id
                    ? 'bg-violet-100 dark:bg-violet-500/20'
                    : 'hover:bg-slate-100 dark:hover:bg-slate-800/40'
                }`}
                onClick={() => setEditing(ex)}
              >
                <div className="flex items-center gap-2">
                  <span className="flex-1 text-sm font-medium text-slate-900 dark:text-white truncate">
                    #{ex.id} · {ex.title_fr || ex.title_en || t('exercisePicker.untitled')}
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleInsert(ex); }}
                    className="p-1 rounded text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-500/20"
                    title={t('exercisePicker.insertHint')}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(ex); }}
                    className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="text-[11px] text-slate-400 dark:text-gray-500 mt-0.5">
                  {ex.language} · {ex.test_cases?.length || 0} tests
                </div>
              </div>
            ))}
          </div>

          {/* Form */}
          <div className="col-span-8 overflow-y-auto p-4">
            {!editing ? (
              <p className="text-sm text-slate-500 dark:text-gray-400 text-center py-12">
                {t('exercisePicker.selectHint')}
              </p>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    className="input-field"
                    placeholder={t('exercisePicker.titleFr')}
                    value={editing.title_fr || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, title_fr: e.target.value }))}
                  />
                  <input
                    className="input-field"
                    placeholder={t('exercisePicker.titleEn')}
                    value={editing.title_en || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, title_en: e.target.value }))}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <textarea
                    className="input-field h-24 text-sm"
                    placeholder={t('exercisePicker.promptFr')}
                    value={editing.prompt_fr || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, prompt_fr: e.target.value }))}
                  />
                  <textarea
                    className="input-field h-24 text-sm"
                    placeholder={t('exercisePicker.promptEn')}
                    value={editing.prompt_en || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, prompt_en: e.target.value }))}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <select
                    className="input-field w-32"
                    value={editing.language}
                    onChange={(e) => {
                      const lang = e.target.value;
                      setEditing((p) => ({
                        ...p,
                        language: lang,
                        starter_code: STARTER_BY_LANG[lang] || p.starter_code,
                      }));
                    }}
                  >
                    <option value="py3">Python 3</option>
                    <option value="cpp">C++</option>
                    <option value="c">C</option>
                    <option value="java">Java</option>
                  </select>
                  <input
                    type="number"
                    min="100" max="30000"
                    className="input-field w-32"
                    placeholder="ms"
                    value={editing.time_limit_ms || 2000}
                    onChange={(e) => setEditing((p) => ({ ...p, time_limit_ms: parseInt(e.target.value, 10) || 2000 }))}
                  />
                  <span className="text-xs text-slate-400">{t('exercisePicker.timeLimit')}</span>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400 mb-1 block">
                    {t('exercisePicker.starterCode')}
                  </label>
                  <textarea
                    className="input-field h-32 font-mono text-xs"
                    spellCheck={false}
                    value={editing.starter_code || ''}
                    onChange={(e) => setEditing((p) => ({ ...p, starter_code: e.target.value }))}
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400">
                      {t('exercisePicker.testCases')}
                    </label>
                    <button
                      onClick={() => setEditing((p) => ({ ...p, test_cases: [...(p.test_cases || []), { ...DEFAULT_TEST_CASE }] }))}
                      className="text-xs text-violet-600 hover:text-violet-500 dark:text-violet-400"
                    >
                      + {t('exercisePicker.addTest')}
                    </button>
                  </div>
                  <div className="space-y-2">
                    {(editing.test_cases || []).map((tc, i) => (
                      <div key={i} className="border border-gray-200 dark:border-slate-700/50 rounded p-2">
                        <div className="flex items-center gap-2 mb-1 text-xs">
                          <span className="font-mono">#{i + 1}</span>
                          <label className="inline-flex items-center gap-1">
                            <input
                              type="checkbox"
                              checked={tc.is_sample !== false}
                              onChange={(e) => setEditing((p) => {
                                const cases = [...p.test_cases];
                                cases[i] = { ...cases[i], is_sample: e.target.checked };
                                return { ...p, test_cases: cases };
                              })}
                            />
                            {t('exercisePicker.sample')}
                          </label>
                          <button
                            onClick={() => setEditing((p) => ({
                              ...p,
                              test_cases: p.test_cases.filter((_, j) => j !== i),
                            }))}
                            className="ml-auto text-slate-400 hover:text-red-500"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <textarea
                            className="input-field font-mono text-xs h-20"
                            placeholder={t('exercisePicker.input')}
                            value={tc.input || ''}
                            onChange={(e) => setEditing((p) => {
                              const cases = [...p.test_cases];
                              cases[i] = { ...cases[i], input: e.target.value };
                              return { ...p, test_cases: cases };
                            })}
                          />
                          <textarea
                            className="input-field font-mono text-xs h-20"
                            placeholder={t('exercisePicker.expected')}
                            value={tc.expected || ''}
                            onChange={(e) => setEditing((p) => {
                              const cases = [...p.test_cases];
                              cases[i] = { ...cases[i], expected: e.target.value };
                              return { ...p, test_cases: cases };
                            })}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-slate-700/50">
                  <button onClick={handleSave} className="btn-primary inline-flex items-center gap-2">
                    <Save className="w-4 h-4" />
                    {t('exercisePicker.save')}
                  </button>
                  {editing.id && (
                    <button
                      onClick={() => handleInsert(editing)}
                      className="btn-secondary inline-flex items-center gap-2"
                    >
                      {t('exercisePicker.insert')}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
