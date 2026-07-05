import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  X, Upload, FileText, FileDown, Code, FileType, FlaskConical,
  RefreshCw, Lock, Globe, Save, Trash2,
} from 'lucide-react';
import {
  createContest, updateContest,
  uploadProblemStatement, deleteProblemStatement,
  rescoreContest, importDomjudgePackage, rejudgeAllIcpc,
} from '../../api';
import AdminHints from '../AdminHints';
import IcpcProblemsPanel from '../IcpcProblemsPanel';
import IcpcStatsPanel from '../IcpcStatsPanel';
import ParticipantsAllowlist from './ParticipantsAllowlist';
import TestScoringModal from './TestScoringModal';
import { useConfirm } from '../Confirm';
import { toUtcIso, toLocalInputValue } from '../../utils/datetime';
import { extractErrorMessage } from '../../utils/apiError';

const DEFAULT_SCRIPT = '# Variables disponibles : instance_data, submission_data\n# Définissez la variable score\n\nlines = submission_data.strip().split("\\n")\nscore = len(lines)\n';

// Create/edit contest modal. Remounted per open, so all the form state
// initializes fresh from the ``contest`` prop (a *full* contest as
// returned by getContest, or null for create mode - where ``initialKind``
// comes from the kind picker). ``onChange`` asks Admin.jsx to reload the
// contest list without closing the modal (PDF swap, rescore); ``onClose``
// just closes.
export default function ContestFormModal({ contest: initialContest, initialKind, users, onClose, onChange }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  // Local copy so PDF upload/removal can swap in the fresh contest
  // payload returned by the backend without closing the modal.
  const [contest, setContest] = useState(initialContest);
  const [contestForm, setContestForm] = useState(() =>
    initialContest
      ? {
          title: initialContest.title || '',
          description: initialContest.description || '',
          problem_statement: initialContest.problem_statement || '',
          visible_at: toLocalInputValue(initialContest.visible_at),
          start_time: toLocalInputValue(initialContest.start_time),
          end_time: toLocalInputValue(initialContest.end_time),
          hidden_at: toLocalInputValue(initialContest.hidden_at),
          freeze_scoreboard_at: toLocalInputValue(initialContest.freeze_scoreboard_at),
          participation_mode: initialContest.participation_mode || 'team',
          is_public: initialContest.is_public !== false,
          practice_mode: !!initialContest.practice_mode,
          kind: initialContest.kind || 'output',
          dedup_block: !!initialContest.dedup_block,
          min_seconds_between_submits: initialContest.min_seconds_between_submits || 0,
          max_submissions_per_instance: initialContest.max_submissions_per_instance ?? '',
          output_validator_script: initialContest.output_validator_script || '',
          scoring_script: initialContest.scoring_script || '',
        }
      : {
          title: '', description: '', problem_statement: '',
          visible_at: '', start_time: '', end_time: '', hidden_at: '', freeze_scoreboard_at: '',
          participation_mode: 'team',
          is_public: true,
          practice_mode: false,
          kind: initialKind,
          dedup_block: false,
          min_seconds_between_submits: 0,
          max_submissions_per_instance: '',
          output_validator_script: '',
          scoring_script: DEFAULT_SCRIPT,
        }
  );
  // A PDF selected at creation time. Uploaded as a follow-up call after
  // the contest has an ID.
  const [createPdfFile, setCreatePdfFile] = useState(null);
  // ICPC-only: DOMjudge package file to import right after the contest
  // is created (so the admin doesn't need a second edit-save round trip).
  const [createIcpcPackage, setCreateIcpcPackage] = useState(null);
  const [rescoring, setRescoring] = useState(false);
  const [rejudging, setRejudging] = useState(false);
  // "score" | "validate" | null - opens the test-scoring modal.
  const [testScoringMode, setTestScoringMode] = useState(null);

  const handleContestSubmit = async (e) => {
    e.preventDefault();
    const isIcpc = contestForm.kind === 'icpc';
    try {
      // Strip Hashcode-only fields when saving an ICPC contest so the
      // backend doesn't store stale data that would confuse the judging
      // pipeline if someone flips the kind later.
      const commonPayload = {
        title: contestForm.title,
        description: contestForm.description,
        visible_at: toUtcIso(contestForm.visible_at),
        start_time: toUtcIso(contestForm.start_time),
        end_time: toUtcIso(contestForm.end_time),
        hidden_at: toUtcIso(contestForm.hidden_at),
        freeze_scoreboard_at: toUtcIso(contestForm.freeze_scoreboard_at),
        participation_mode: contestForm.participation_mode,
        is_public: contestForm.is_public,
        kind: contestForm.kind,
        practice_mode: contestForm.practice_mode,
        dedup_block: contestForm.dedup_block,
        min_seconds_between_submits: parseInt(contestForm.min_seconds_between_submits || 0, 10) || 0,
      };
      const payload = isIcpc
        ? commonPayload
        : {
            ...commonPayload,
            problem_statement: contestForm.problem_statement,
            scoring_script: contestForm.scoring_script,
            output_validator_script: (contestForm.output_validator_script || '').trim() || null,
            max_submissions_per_instance:
              contestForm.max_submissions_per_instance === '' || contestForm.max_submissions_per_instance == null
                ? null
                : parseInt(contestForm.max_submissions_per_instance, 10),
          };

      if (contest) {
        await updateContest(contest.id, payload);
        toast.success(t('admin.contests.toastUpdated'));
      } else {
        const { data: created } = await createContest(payload);
        // Output contest: optional per-contest PDF.
        if (!isIcpc && createPdfFile) {
          const MAX_BYTES = 10 * 1024 * 1024;
          if (createPdfFile.size > MAX_BYTES) {
            toast.error(t('admin.form.toastPdfTooLarge'));
          } else {
            try {
              await uploadProblemStatement(created.id, createPdfFile);
            } catch (err) {
              toast.error(extractErrorMessage(err, t('admin.form.toastPdfUploadFailed')));
            }
          }
        }
        // ICPC contest: if the admin attached a DOMjudge package, import it
        // now so the contest ships with problems + testcases on first save.
        if (isIcpc && createIcpcPackage) {
          try {
            const { data } = await importDomjudgePackage(created.id, createIcpcPackage);
            toast.success(t('admin.form.toastImportOk', {
              problems: data.problems_imported,
              testcases: data.testcases_imported,
            }));
          } catch (err) {
            toast.error(extractErrorMessage(err, t('admin.form.toastImportFailed')));
          }
        }
        toast.success(t('admin.contests.toastCreated'));
      }
      onChange();
      onClose();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.contests.toastFailed')));
    }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !contest) return;
    const MAX_BYTES = 10 * 1024 * 1024;
    if (file.size > MAX_BYTES) {
      toast.error(t('admin.form.toastPdfTooLarge'));
      return;
    }
    const toastId = toast.loading(t('admin.form.toastPdfUploading'));
    try {
      const { data } = await uploadProblemStatement(contest.id, file);
      setContest(data);
      toast.success(t('admin.form.toastPdfUploaded'), { id: toastId });
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastPdfUploadFailed')), { id: toastId });
    }
  };

  const handlePdfRemove = async () => {
    if (!contest) return;
    const ok = await confirm({
      message: t('admin.form.confirmRemovePdf'),
      danger: true,
    });
    if (!ok) return;
    const toastId = toast.loading(t('admin.form.toastPdfRemoving'));
    try {
      const { data } = await deleteProblemStatement(contest.id);
      setContest(data);
      toast.success(t('admin.form.toastPdfRemoved'), { id: toastId });
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastPdfRemoveFailed')), { id: toastId });
    }
  };

  // Shared uploader for scoring + validator scripts. ``field`` is the
  // key on contestForm to write the uploaded contents to.
  const uploadScriptInto = async (e, field) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const MAX_BYTES = 256 * 1024;
    if (file.size > MAX_BYTES) {
      toast.error(t('admin.form.toastScriptTooLarge'));
      return;
    }
    try {
      const text = await file.text();
      setContestForm((f) => ({ ...f, [field]: text }));
      toast.success(t('admin.form.toastLoaded', { name: file.name }));
    } catch {
      toast.error(t('admin.form.toastScriptReadFailed'));
    }
  };
  const handleScriptUpload = (e) => uploadScriptInto(e, 'scoring_script');
  const handleValidatorUpload = (e) => uploadScriptInto(e, 'output_validator_script');

  const downloadAsPy = (content, baseName) => {
    if (!content) return;
    const safe = (contestForm.title || baseName).replace(/[^a-zA-Z0-9._-]+/g, '_');
    const blob = new Blob([content], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safe}-${baseName}.py`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };
  const handleScriptDownload = () =>
    downloadAsPy(contestForm.scoring_script, 'scoring');
  const handleValidatorDownload = () =>
    downloadAsPy(contestForm.output_validator_script, 'validator');

  const handleRescore = async () => {
    if (!contest) return;
    const ok = await confirm({
      message: t('admin.form.confirmRescore', { title: contest.title }),
    });
    if (!ok) return;
    setRescoring(true);
    try {
      const { data } = await rescoreContest(contest.id);
      toast.success(t('admin.form.toastRescoreDone', {
        s: data.succeeded, u: data.unchanged, f: data.failed,
      }));
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastRescoreFailed')));
    } finally {
      setRescoring(false);
    }
  };

  // ICPC counterpart of handleRescore: re-queue every submission of the
  // contest through the judging pipeline.
  const handleRejudgeAll = async () => {
    if (!contest) return;
    const ok = await confirm({
      message: t('admin.contests.rejudgeAllConfirm', { title: contest.title }),
    });
    if (!ok) return;
    setRejudging(true);
    try {
      const { data } = await rejudgeAllIcpc(contest.id);
      toast.success(t('admin.contests.rejudgeAllDone', { count: data.count }));
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.contests.rejudgeAllFailed')));
    } finally {
      setRejudging(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto">
        <div className="card p-6 w-full max-w-3xl my-8 animate-fade-in" role="dialog" aria-modal="true" aria-labelledby="contest-form-title">
          <div className="flex items-center justify-between mb-6">
            <h2 id="contest-form-title" className="text-xl font-bold text-zinc-900 dark:text-white">
              {contest ? t('admin.form.editTitle') : t('admin.form.createTitle')}
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
              aria-label={t('admin.form.closeAria')}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleContestSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">{t('admin.form.titleField')}</label>
              <input
                type="text"
                className="input-field"
                value={contestForm.title}
                onChange={(e) => setContestForm({ ...contestForm, title: e.target.value })}
                placeholder={t('admin.form.titlePlaceholder')}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">{t('admin.form.descriptionField')}</label>
              <input
                type="text"
                className="input-field"
                value={contestForm.description}
                onChange={(e) => setContestForm({ ...contestForm, description: e.target.value })}
                placeholder={t('admin.form.descriptionPlaceholder')}
              />
            </div>

            {contestForm.kind !== 'icpc' && (
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                {t('admin.form.statementField')}
              </label>
              <textarea
                className="input-field min-h-[200px] font-mono text-sm"
                value={contestForm.problem_statement}
                onChange={(e) => setContestForm({ ...contestForm, problem_statement: e.target.value })}
                placeholder={t('admin.form.statementPlaceholder')}
              />
            </div>
            )}

            {!contest && contestForm.kind !== 'icpc' && (
              <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 dark:bg-zinc-800/30 dark:border-zinc-700/40">
                <label className="block text-sm font-medium text-zinc-700 mb-2 flex items-center gap-2 dark:text-zinc-300">
                  <FileType className="w-4 h-4 text-accent-500 dark:text-accent-400" />
                  {t('admin.form.pdfLabel')}
                </label>
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(e) => setCreatePdfFile(e.target.files?.[0] || null)}
                  className="input-field text-sm py-2 file:mr-2 file:py-0.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-accent-600 file:text-white"
                />
                {createPdfFile && (
                  <p className="text-xs text-zinc-500 mt-1.5 dark:text-zinc-500">
                    {createPdfFile.name}
                  </p>
                )}
                <p className="text-xs text-zinc-500 mt-1.5 dark:text-zinc-500">
                  {t('admin.form.pdfHint')}
                </p>
              </div>
            )}

            {contest && contestForm.kind !== 'icpc' && (
              <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 dark:bg-zinc-800/30 dark:border-zinc-700/40">
                <label className="block text-sm font-medium text-zinc-700 mb-2 flex items-center gap-2 dark:text-zinc-300">
                  <FileType className="w-4 h-4 text-accent-500 dark:text-accent-400" />
                  {t('admin.form.pdfLabel')}
                </label>
                {contest.has_problem_statement_pdf ? (
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-accent-500 flex-shrink-0 dark:text-accent-400" />
                      <span className="text-sm text-zinc-700 truncate dark:text-zinc-200" title={contest.problem_statement_pdf_name}>
                        {contest.problem_statement_pdf_name || t('admin.form.pdfFilename')}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200">
                        <Upload className="w-3.5 h-3.5" />
                        {t('admin.form.replacePdf')}
                        <input
                          type="file"
                          accept="application/pdf,.pdf"
                          className="hidden"
                          onChange={handlePdfUpload}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={handlePdfRemove}
                        className="text-xs font-medium px-3 py-1.5 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-600 transition-colors flex items-center gap-1.5 dark:text-red-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {t('admin.form.removePdf')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <label className="cursor-pointer inline-flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200">
                      <Upload className="w-4 h-4" />
                      {t('admin.form.uploadPdf')}
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        className="hidden"
                        onChange={handlePdfUpload}
                      />
                    </label>
                    <p className="text-xs text-zinc-500 mt-2 dark:text-zinc-500">
                      {t('admin.form.pdfHint')}
                    </p>
                  </>
                )}
              </div>
            )}

            <div className="space-y-3">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                    {t('admin.form.visibleAt')}
                  </label>
                  <input
                    type="datetime-local"
                    className="input-field"
                    value={contestForm.visible_at}
                    onChange={(e) => setContestForm({ ...contestForm, visible_at: e.target.value })}
                  />
                  <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                    {t('admin.form.visibleAtHint')}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                    {t('admin.form.startTime')}
                  </label>
                  <input
                    type="datetime-local"
                    className="input-field"
                    value={contestForm.start_time}
                    onChange={(e) => setContestForm({ ...contestForm, start_time: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                    {t('admin.form.endTime')}
                  </label>
                  <input
                    type="datetime-local"
                    className="input-field"
                    value={contestForm.end_time}
                    onChange={(e) => setContestForm({ ...contestForm, end_time: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                    {t('admin.form.hiddenAt')}
                  </label>
                  <input
                    type="datetime-local"
                    className="input-field"
                    value={contestForm.hidden_at}
                    onChange={(e) => setContestForm({ ...contestForm, hidden_at: e.target.value })}
                  />
                  <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                    {t('admin.form.hiddenAtHint')}
                  </p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('admin.form.freezeLabel')}
                </label>
                <input
                  type="datetime-local"
                  className="input-field"
                  value={contestForm.freeze_scoreboard_at}
                  onChange={(e) => setContestForm({ ...contestForm, freeze_scoreboard_at: e.target.value })}
                />
                <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                  {t('admin.form.freezeHint')}
                </p>
              </div>
            </div>

            {contestForm.kind !== 'icpc' && (
            <div>
              <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  <Code className="w-4 h-4 inline mr-1" />
                  {t('admin.form.scriptLabel')}
                </label>
                <div className="flex gap-2">
                  <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200">
                    <Upload className="w-3.5 h-3.5" />
                    {t('admin.form.uploadPy')}
                    <input
                      type="file"
                      accept=".py,text/x-python,text/plain"
                      className="hidden"
                      onChange={handleScriptUpload}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={handleScriptDownload}
                    disabled={!contestForm.scoring_script}
                    className="text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
                    title={t('admin.form.downloadPyTooltip')}
                  >
                    <FileDown className="w-3.5 h-3.5" />
                    {t('admin.form.downloadPy')}
                  </button>
                  {contest && (
                    <button
                      type="button"
                      onClick={() => setTestScoringMode('score')}
                      className="text-xs font-medium px-3 py-1.5 rounded-md bg-accent-600/10 hover:bg-accent-600/20 border border-accent-500/30 text-accent-700 transition-colors flex items-center gap-1.5 dark:bg-accent-600/20 dark:hover:bg-accent-600/30 dark:text-accent-300"
                      title={t('admin.form.testScriptTooltip')}
                    >
                      <FlaskConical className="w-3.5 h-3.5" />
                      {t('admin.form.testScript')}
                    </button>
                  )}
                  {contest && (
                    <button
                      type="button"
                      onClick={handleRescore}
                      disabled={rescoring}
                      className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300"
                      title={t('admin.form.rescoreTooltip')}
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${rescoring ? 'animate-spin' : ''}`} />
                      {rescoring ? t('admin.form.rescoring') : t('admin.form.rescoreAll')}
                    </button>
                  )}
                </div>
              </div>
              <textarea
                className="input-field min-h-[150px] font-mono text-sm"
                value={contestForm.scoring_script}
                onChange={(e) => setContestForm({ ...contestForm, scoring_script: e.target.value })}
                placeholder={t('admin.form.scriptPlaceholder')}
                spellCheck={false}
              />
              <p className="text-xs text-zinc-500 mt-1.5 dark:text-zinc-500">
                {t('admin.form.scriptHint1', {
                  args: 'instance_data, submission_data',
                  score: 'score',
                })}{' '}
                {t('admin.form.scriptHint2', { mods: 'math, re, json' })}
              </p>
            </div>
            )}

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('admin.form.participationModeLabel')}
                </label>
                <select
                  className="input-field"
                  value={contestForm.participation_mode}
                  onChange={(e) => setContestForm({ ...contestForm, participation_mode: e.target.value })}
                >
                  <option value="team">{t('admin.form.participationModeTeam')}</option>
                  <option value="solo">{t('admin.form.participationModeSolo')}</option>
                  <option value="both">{t('admin.form.participationModeBoth')}</option>
                </select>
                <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                  {t('admin.form.participationModeHint')}
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('admin.form.accessLabel')}
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setContestForm({ ...contestForm, is_public: true })}
                    className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      contestForm.is_public
                        ? 'bg-accent-600 text-white border-accent-600'
                        : 'bg-white text-zinc-700 border-zinc-300 hover:bg-zinc-100 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700 dark:hover:bg-zinc-700'
                    }`}
                  >
                    <Globe className="w-4 h-4" />
                    {t('admin.form.accessPublic')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setContestForm({ ...contestForm, is_public: false })}
                    className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      !contestForm.is_public
                        ? 'bg-accent-600 text-white border-accent-600'
                        : 'bg-white text-zinc-700 border-zinc-300 hover:bg-zinc-100 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700 dark:hover:bg-zinc-700'
                    }`}
                  >
                    <Lock className="w-4 h-4" />
                    {t('admin.form.accessPrivate')}
                  </button>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                  {contestForm.is_public
                    ? t('admin.form.accessPublicHint')
                    : t('admin.form.accessPrivateHint')}
                </p>
              </div>
            </div>

            {/* Kind is chosen in the picker modal. Show it as a
                read-only badge here so the admin always sees which
                kind of contest they're editing. */}
            <div className="flex items-center gap-2 text-xs">
              <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md font-medium ${
                contestForm.kind === 'icpc'
                  ? 'bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300'
                  : 'bg-accent-500/15 text-accent-700 border border-accent-500/30 dark:text-accent-300'
              }`}>
                {contestForm.kind === 'icpc'
                  ? <><Code className="w-3.5 h-3.5" /> {t('admin.form.kindIcpc')}</>
                  : <><FlaskConical className="w-3.5 h-3.5" /> {t('admin.form.kindOutput')}</>
                }
              </span>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                {contestForm.kind === 'icpc'
                  ? t('admin.form.kindIcpcHint')
                  : t('admin.form.kindOutputHint')}
              </span>
            </div>

            {/* DOMjudge package importer - visible during create
                (stages the file for post-create upload) and during
                edit (imports immediately). */}
            {contestForm.kind === 'icpc' && (
              <div className="rounded-lg border-2 border-dashed border-sky-500/40 bg-sky-500/5 p-4">
                <label className="block text-sm font-semibold text-zinc-700 mb-2 flex items-center gap-2 dark:text-zinc-300">
                  <Upload className="w-4 h-4 text-sky-500 dark:text-sky-400" />
                  {t('admin.form.importDomjudge')}
                </label>
                <input
                  type="file"
                  accept=".zip,application/zip"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    if (contest) {
                      // Edit mode: import right away.
                      try {
                        const { data } = await importDomjudgePackage(contest.id, f);
                        toast.success(t('admin.form.toastImportOk', {
                          problems: data.problems_imported,
                          testcases: data.testcases_imported,
                        }));
                      } catch (err) {
                        toast.error(extractErrorMessage(err, t('admin.form.toastImportFailed')));
                      } finally {
                        e.target.value = '';
                      }
                    } else {
                      // Create mode: stage the file; handleContestSubmit
                      // uploads it after the contest is created.
                      setCreateIcpcPackage(f);
                    }
                  }}
                  className="input-field text-sm py-2 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-sky-600 file:text-white"
                />
                {!contest && createIcpcPackage && (
                  <p className="text-xs text-sky-700 mt-1.5 dark:text-sky-300">
                    {t('admin.form.icpcPackageStaged', { name: createIcpcPackage.name })}
                  </p>
                )}
                {!contest && !createIcpcPackage && (
                  <p className="text-xs text-amber-700 mt-1.5 dark:text-amber-300">
                    {t('admin.form.icpcNoProblemsYet')}
                  </p>
                )}
                <p className="text-[11px] text-zinc-500 mt-1.5 dark:text-zinc-400">
                  {t('admin.form.importDomjudgeHint')}
                </p>
              </div>
            )}

            <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={!!contestForm.practice_mode}
                onChange={(e) => setContestForm({ ...contestForm, practice_mode: e.target.checked })}
              />
              <span>{t('admin.form.practiceMode')}</span>
              <span className="text-[11px] text-zinc-400 ml-1 dark:text-zinc-500">
                {t('admin.form.practiceModeHint')}
              </span>
            </label>

            <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 space-y-3 dark:bg-zinc-800/30 dark:border-zinc-700/40">
              <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                {t('admin.form.hardeningHeading')}
              </h4>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!contestForm.dedup_block}
                  onChange={(e) => setContestForm({ ...contestForm, dedup_block: e.target.checked })}
                />
                <span>{t('admin.form.dedupBlock')}</span>
                <span className="text-[11px] text-zinc-400 ml-1 dark:text-zinc-500">
                  {t('admin.form.dedupBlockHint')}
                </span>
              </label>
              <div className={contestForm.kind === 'icpc' ? '' : 'grid sm:grid-cols-2 gap-3'}>
                <div>
                  <label className="block text-xs font-medium text-zinc-600 mb-1 dark:text-zinc-400">
                    {t('admin.form.cooldown')}
                  </label>
                  <input
                    type="number"
                    min={0}
                    className="input-field text-sm py-2"
                    value={contestForm.min_seconds_between_submits}
                    onChange={(e) => setContestForm({ ...contestForm, min_seconds_between_submits: e.target.value })}
                  />
                </div>
                {contestForm.kind !== 'icpc' && (
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1 dark:text-zinc-400">
                      {t('admin.form.quota')}
                    </label>
                    <input
                      type="number"
                      min={0}
                      className="input-field text-sm py-2"
                      placeholder={t('admin.form.quotaPlaceholder')}
                      value={contestForm.max_submissions_per_instance}
                      onChange={(e) => setContestForm({ ...contestForm, max_submissions_per_instance: e.target.value })}
                    />
                  </div>
                )}
              </div>
              {contestForm.kind !== 'icpc' && (
                <div>
                  <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                    <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      {t('admin.form.validator')}
                    </label>
                    <div className="flex gap-2">
                      <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200">
                        <Upload className="w-3.5 h-3.5" />
                        {t('admin.form.uploadPy')}
                        <input
                          type="file"
                          accept=".py,text/x-python,text/plain"
                          className="hidden"
                          onChange={handleValidatorUpload}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={handleValidatorDownload}
                        disabled={!contestForm.output_validator_script}
                        className="text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
                        title={t('admin.form.downloadPyTooltip')}
                      >
                        <FileDown className="w-3.5 h-3.5" />
                        {t('admin.form.downloadPy')}
                      </button>
                      {contest && (
                        <button
                          type="button"
                          onClick={() => setTestScoringMode('validate')}
                          disabled={!contestForm.output_validator_script}
                          className="text-xs font-medium px-3 py-1.5 rounded-md bg-accent-600/10 hover:bg-accent-600/20 border border-accent-500/30 text-accent-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-accent-600/20 dark:hover:bg-accent-600/30 dark:text-accent-300"
                          title={t('admin.form.testValidatorTooltip')}
                        >
                          <FlaskConical className="w-3.5 h-3.5" />
                          {t('admin.form.testScript')}
                        </button>
                      )}
                      {contest && (
                        <button
                          type="button"
                          onClick={handleRescore}
                          disabled={rescoring}
                          className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300"
                          title={t('admin.form.rescoreTooltip')}
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${rescoring ? 'animate-spin' : ''}`} />
                          {rescoring ? t('admin.form.rescoring') : t('admin.form.rescoreAll')}
                        </button>
                      )}
                    </div>
                  </div>
                  <textarea
                    className="input-field text-xs font-mono min-h-[120px]"
                    placeholder={t('admin.form.validatorPlaceholder')}
                    value={contestForm.output_validator_script}
                    onChange={(e) => setContestForm({ ...contestForm, output_validator_script: e.target.value })}
                  />
                  <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-500">
                    {t('admin.form.validatorHint')}
                  </p>
                </div>
              )}
            </div>

            {contest && contestForm.kind !== 'icpc' && <AdminHints contestId={contest.id} />}
            {contest && contestForm.kind === 'icpc' && (
              // The `key` forces a remount when the admin jumps
              // between different contests from the list - without
              // it React reuses the same component instance and
              // the inner state briefly shows the previous
              // contest's problems under the new id.
              <>
                <div className="flex items-center justify-between gap-3 flex-wrap bg-zinc-50 border border-zinc-200 rounded-lg p-3 dark:bg-zinc-800/30 dark:border-zinc-700/40">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      {t('admin.contests.rejudgeAllHeading')}
                    </p>
                    <p className="text-[11px] text-zinc-400 mt-0.5 dark:text-zinc-500">
                      {t('admin.contests.rejudgeAllLeagueHint')}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRejudgeAll}
                    disabled={rejudging}
                    className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300"
                    title={t('admin.contests.rejudgeAllTooltip')}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${rejudging ? 'animate-spin' : ''}`} />
                    {rejudging ? t('admin.contests.rejudgeAllRunning') : t('admin.contests.rejudgeAll')}
                  </button>
                </div>
                <IcpcProblemsPanel key={contest.id} contestId={contest.id} />
                <IcpcStatsPanel key={`stats-${contest.id}`} contestId={contest.id} />
              </>
            )}

            {contest && !contestForm.is_public && (
              <ParticipantsAllowlist
                contest={contest}
                participationMode={contestForm.participation_mode}
                users={users}
              />
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary"
              >
                {t('common.cancel')}
              </button>
              <button type="submit" className="btn-primary">
                <Save className="w-4 h-4 mr-2 inline" />
                {contest ? t('admin.form.saveUpdate') : t('admin.form.saveCreate')}
              </button>
            </div>
          </form>
        </div>
      </div>

      {testScoringMode && contest && (
        <TestScoringModal
          contest={contest}
          mode={testScoringMode}
          scoringScript={contestForm.scoring_script}
          validatorScript={contestForm.output_validator_script}
          onClose={() => setTestScoringMode(null)}
        />
      )}
    </>
  );
}
