import { useState } from 'react';
import { Upload, FileText as FileTextIcon, Code2 } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { submitSolution, submitSolutionCode } from '../../api';
import { useTheme } from '../../ThemeContext';
import { formatScore } from '../../utils/format';
import { extractErrorMessage } from '../../utils/apiError';

// Solution submit card: team/solo toggle, instance picker, and the three
// upload modes (file / raw output pasted as code / compile+run source).
// Owns everything submit-local; the shared team/kind selection and the
// submission list live in the parent (``onSubmitted`` refreshes the list).
export default function SubmitSolutionForm({
  contest, teams, submitKind, setSubmitKind, selectedTeam, setSelectedTeam,
  submissions, sourceLanguages, onSubmitted,
}) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [selectedInstance, setSelectedInstance] = useState('');
  const [file, setFile] = useState(null);
  const [submitMode, setSubmitMode] = useState('file'); // 'file' | 'code' | 'source'
  const [codeText, setCodeText] = useState('');
  // For submitMode === 'source', the server will compile + run this code.
  const [sourceLanguage, setSourceLanguage] = useState('py3');
  const [uploading, setUploading] = useState(false);

  const pollSubmissionStatus = async (submissionId) => {
    // Poll until the async scoring settles (max ~30s).
    for (let i = 0; i < 60; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((res) => setTimeout(res, 500));
      try {
        // eslint-disable-next-line no-await-in-loop
        const { data } = await (await import('../../api')).getSubmission(submissionId);
        if (data.status !== 'pending') return data;
      } catch {
        // keep polling briefly
      }
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedInstance) {
      toast.error(t('contest.toastSelectFields'));
      return;
    }
    if (submitKind === 'team' && !selectedTeam) {
      toast.error(t('contest.toastSelectFields'));
      return;
    }
    let blob;
    let fileName;
    if (submitMode === 'file') {
      if (!file) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
      blob = file;
      fileName = file.name;
    } else if (submitMode === 'source') {
      if (!codeText.trim()) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
    } else {
      const text = codeText;
      if (!text.trim()) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
      blob = new Blob([text], { type: 'text/plain' });
      fileName = 'submission.py';
    }
    setUploading(true);
    try {
      const formData = new FormData();
      if (submitMode === 'source') {
        // Compile+run path: server runs the program, captures stdout,
        // and feeds THAT to the validator + scorer.
        formData.append('language', sourceLanguage);
        formData.append('source', codeText);
      } else {
        formData.append('file', blob, fileName);
      }
      if (submitKind === 'team') {
        formData.append('team_id', selectedTeam);
      }
      const submitFn = submitMode === 'source' ? submitSolutionCode : submitSolution;
      const { data } = await submitFn(contest.id, selectedInstance, formData);
      toast.loading(t('contest.scoringInProgress'), { id: `sub-${data.id}` });
      const final = await pollSubmissionStatus(data.id);
      toast.dismiss(`sub-${data.id}`);
      if (!final) {
        toast.error(t('contest.scoringTakingLong'));
      } else if (final.status === 'scored') {
        toast.success(t('contest.toastScoreFormat', { score: formatScore(final.score) }));
      } else {
        const msg = (final.error_message || t('contest.toastUnknownError')).slice(0, 160);
        toast.error(t('contest.toastScoringError', { msg }));
      }
      setFile(null);
      setCodeText('');
      await onSubmitted();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('contest.toastSubmitFailed')));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card p-6">
      <h2 className="text-lg font-bold text-zinc-900 mb-4 flex items-center gap-2 dark:text-white">
        <Upload className="w-5 h-5 text-accent-500 dark:text-accent-400" />
        {t('contest.submitSolution')}
      </h2>
      <form
        onSubmit={handleSubmit}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !uploading) {
            e.preventDefault();
            e.currentTarget.requestSubmit();
          }
        }}
        className="space-y-4"
      >
        {contest.participation_mode === 'both' && (
          <div className="inline-flex rounded-lg border border-zinc-200 p-0.5 dark:border-zinc-700">
            <button
              type="button"
              onClick={() => setSubmitKind('team')}
              disabled={teams.length === 0}
              className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                submitKind === 'team'
                  ? 'bg-accent-600 text-white'
                  : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed'
              }`}
            >
              {t('contest.submitAsTeam')}
            </button>
            <button
              type="button"
              onClick={() => setSubmitKind('solo')}
              className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                submitKind === 'solo'
                  ? 'bg-accent-600 text-white'
                  : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              {t('contest.submitAsSolo')}
            </button>
          </div>
        )}
        <div className={submitKind === 'team' && teams.length > 1 ? 'grid sm:grid-cols-2 gap-4' : ''}>
          {submitKind === 'team' && teams.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                {t('contest.teamLabel')}
              </label>
              <select
                className="input-field"
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
              >
                {teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('contest.instanceLabel')}
            </label>
            <select
              className="input-field"
              value={selectedInstance}
              onChange={(e) => setSelectedInstance(e.target.value)}
            >
              <option value="">{t('contest.chooseInstance')}</option>
              {contest.instances
                .filter((inst) => inst.is_unlocked)
                .map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.name}
                  </option>
                ))}
            </select>
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-2 gap-2">
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
              {t('contest.fileLabel')}
            </label>
            <div className="inline-flex rounded-lg border border-zinc-200 p-0.5 dark:border-zinc-700">
              <button
                type="button"
                onClick={() => setSubmitMode('file')}
                className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                  submitMode === 'file'
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                }`}
              >
                <FileTextIcon className="w-3.5 h-3.5" />
                {t('contest.modeFile')}
              </button>
              <button
                type="button"
                onClick={() => setSubmitMode('code')}
                className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                  submitMode === 'code'
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                {t('contest.modeCode')}
              </button>
              <button
                type="button"
                onClick={() => setSubmitMode('source')}
                className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                  submitMode === 'source'
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                }`}
                title={t('contest.modeSourceHint')}
              >
                <Code2 className="w-3.5 h-3.5" />
                {t('contest.modeSource')}
              </button>
            </div>
          </div>

          {submitMode === 'source' && (
            <div className="mb-2 flex items-center gap-2">
              <label className="text-xs text-zinc-500 dark:text-zinc-400">
                {t('contest.sourceLanguage')}
              </label>
              <select
                className="input-field text-xs py-1 px-2"
                value={sourceLanguage}
                onChange={(e) => setSourceLanguage(e.target.value)}
              >
                {sourceLanguages.map((l) => (
                  <option key={l.id} value={l.id}>{l.display_name}</option>
                ))}
              </select>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                {t('contest.modeSourceHint')}
              </span>
            </div>
          )}

          {submitMode === 'file' ? (
            <>
              <div className="relative">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files[0])}
                  className="input-field file:mr-4 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-accent-600 file:text-white hover:file:bg-accent-500 file:cursor-pointer"
                />
              </div>
              {file && (
                <p className="text-sm text-zinc-500 mt-1.5 dark:text-zinc-400">
                  {t('contest.selectedFile', { name: file.name })}
                </p>
              )}
            </>
          ) : (
            <div className="rounded-lg border border-zinc-300 overflow-hidden dark:border-zinc-700">
              <CodeMirror
                value={codeText}
                onChange={(v) => setCodeText(v)}
                extensions={[python()]}
                basicSetup={{ lineNumbers: true, highlightActiveLine: false }}
                theme={theme === 'dark' ? oneDark : 'light'}
                height="260px"
              />
              {submitMode === 'source' && (
                <p className="text-[11px] text-zinc-400 px-2 py-1 bg-zinc-50 dark:bg-zinc-800/40 dark:text-zinc-500">
                  {t('contest.sourceStdinHint')}
                </p>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button type="submit" className="btn-primary" disabled={uploading}>
            {uploading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t('contest.submitting')}
              </span>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2 inline" />
                {t('common.submit')}
              </>
            )}
          </button>
          <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
            {t('contest.submitShortcutHint')}
          </span>
          {contest.max_submissions_per_instance && selectedInstance && (
            <span className="text-[11px] text-zinc-400 dark:text-zinc-500 ml-auto">
              {t('contest.quotaUsed', {
                used: submissions.filter((x) => String(x.instance_id) === String(selectedInstance)).length,
                limit: contest.max_submissions_per_instance,
              })}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
