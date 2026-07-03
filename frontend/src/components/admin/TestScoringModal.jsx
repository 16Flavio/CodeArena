import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlaskConical, X } from 'lucide-react';
import { testScoring } from '../../api';
import { extractErrorMessage } from '../../utils/apiError';

// Dry-run modal for the scoring script ("score" mode) or the output
// validator ("validate" mode) against one of the contest's instances.
// Remounted on every open so the fields always start fresh. The parent
// passes the *editor* versions of both scripts so "use editor script"
// tests the unsaved contents, not what's stored in the DB.
export default function TestScoringModal({ contest, mode, scoringScript, validatorScript, onClose }) {
  const { t } = useTranslation();
  const [testScoringState, setTestScoringState] = useState({
    instance_id: contest?.instances?.[0]?.id ? String(contest.instances[0].id) : '',
    submission_data: '',
    useOverride: true,
    result: null,
    running: false,
  });

  const runTestScoring = async (e) => {
    e.preventDefault();
    if (!contest || !testScoringState.instance_id) return;
    setTestScoringState((s) => ({ ...s, running: true, result: null }));
    try {
      const isValidate = mode === 'validate';
      const payload = {
        instance_id: parseInt(testScoringState.instance_id, 10),
        submission_data: testScoringState.submission_data,
        mode: isValidate ? 'validate' : 'score',
      };
      if (testScoringState.useOverride) {
        if (isValidate) {
          payload.validator_override = validatorScript || '';
        } else {
          payload.script_override = scoringScript;
        }
      }
      const { data } = await testScoring(contest.id, payload);
      setTestScoringState((s) => ({ ...s, running: false, result: data }));
    } catch (err) {
      setTestScoringState((s) => ({
        ...s,
        running: false,
        result: { ok: false, error: extractErrorMessage(err, 'Échec') },
      }));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto">
      <div className="card p-6 w-full max-w-2xl my-8 animate-fade-in" role="dialog" aria-modal="true">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
            <FlaskConical className="w-5 h-5 text-accent-500 dark:text-accent-400" />
            {mode === 'validate'
              ? t('admin.testScoring.titleValidate')
              : t('admin.testScoring.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
            aria-label="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={runTestScoring} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">{t('admin.testScoring.instanceLabel')}</label>
            <select
              className="input-field"
              value={testScoringState.instance_id}
              onChange={(e) => setTestScoringState((s) => ({ ...s, instance_id: e.target.value }))}
              required
            >
              <option value="">{t('admin.testScoring.instancePlaceholder')}</option>
              {(contest.instances || []).map((inst) => (
                <option key={inst.id} value={inst.id}>{inst.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('admin.testScoring.submissionLabel')}
            </label>
            <textarea
              className="input-field font-mono text-xs min-h-[160px]"
              placeholder={t('admin.testScoring.submissionPlaceholder')}
              value={testScoringState.submission_data}
              onChange={(e) => setTestScoringState((s) => ({ ...s, submission_data: e.target.value }))}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={testScoringState.useOverride}
              onChange={(e) => setTestScoringState((s) => ({ ...s, useOverride: e.target.checked }))}
            />
            {t('admin.testScoring.useEditorScript')}
          </label>

          {testScoringState.result && (
            <div
              className={`rounded-lg p-3 border ${
                testScoringState.result.ok
                  ? 'border-emerald-500/30 bg-emerald-500/10'
                  : 'border-red-500/30 bg-red-500/10'
              }`}
            >
              {testScoringState.result.ok ? (
                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                  {mode === 'validate' ? (
                    <>
                      <span className="font-semibold">{t('admin.testScoring.validOk')}</span>
                    </>
                  ) : (
                    <>
                      <span className="font-semibold">{t('admin.testScoring.scoreLabel')}</span>{' '}
                      <span className="font-mono">{testScoringState.result.score}</span>
                    </>
                  )}
                  <span className="text-xs text-zinc-500 ml-3 dark:text-zinc-400">
                    ({testScoringState.result.duration_ms} ms)
                  </span>
                </p>
              ) : (
                <p className="text-sm text-red-700 dark:text-red-300">
                  <span className="font-semibold">
                    {mode === 'validate'
                      ? t('admin.testScoring.invalidLabel')
                      : t('admin.testScoring.errorLabel')}
                  </span>{' '}
                  <span className="font-mono break-all">{testScoringState.result.error}</span>
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">
              {t('admin.testScoring.closeBtn')}
            </button>
            <button type="submit" className="btn-primary text-sm" disabled={testScoringState.running}>
              {testScoringState.running ? t('admin.testScoring.running') : t('admin.testScoring.run')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
