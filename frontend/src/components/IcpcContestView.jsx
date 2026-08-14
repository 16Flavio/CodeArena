import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import {
  ChevronRight, Upload, CheckCircle, XCircle, Clock, AlertCircle,
  Code2, FileText as FileTextIcon, MessageCircle, Copy, Check,
} from 'lucide-react';
import {
  listIcpcProblems, listIcpcLanguages, submitIcpc, getJudging,
  listClarifications, createClarification, answerClarification,
  updateClarification, deleteClarification,
  openStatementPdf, getMyLatestProblemSubmission,
} from '../api';
import { textOn } from '../utils/contrast';
import { useTheme } from '../ThemeContext';
import { useAuth } from '../AuthContext';
import { useConfirm } from './Confirm';
import { extractErrorMessage } from '../utils/apiError';

// Verdict → classes / short label. Matches DOMjudge's short codes.
const VERDICT_STYLE = {
  AC: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30 dark:text-emerald-400',
  WA: 'bg-red-500/15 text-red-700 border-red-500/30 dark:text-red-400',
  TLE: 'bg-amber-500/15 text-amber-700 border-amber-500/30 dark:text-amber-400',
  MLE: 'bg-amber-500/15 text-amber-700 border-amber-500/30 dark:text-amber-400',
  RE: 'bg-red-500/15 text-red-700 border-red-500/30 dark:text-red-400',
  CE: 'bg-zinc-500/15 text-zinc-700 border-zinc-500/30 dark:text-zinc-300',
  pending: 'bg-zinc-200 text-zinc-700 border-zinc-300 dark:bg-zinc-700 dark:text-zinc-300 dark:border-zinc-600',
  // "Not evaluated" - testcase the judge never reached because it short-
  // circuited at an earlier failure (or because the submission stopped at
  // compile-time). Faded so it visually recedes behind the real verdicts.
  unknown: 'bg-zinc-100 text-zinc-400 border-zinc-200 dark:bg-zinc-800/40 dark:text-zinc-500 dark:border-zinc-700/40',
};


// The number worth showing for a run: CPU time when the judge could measure
// it (that's what the time limit is checked against), else the wall clock,
// which also carries interpreter and container startup.
const runMs = (r) => (r && r.cpu_ms != null ? r.cpu_ms : (r ? r.runtime_ms || 0 : 0));

export default function IcpcContestView({ contest, canParticipate, selectedTeamId }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const { user } = useAuth();
  const confirm = useConfirm();
  const [problems, setProblems] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [activeProblemId, setActiveProblemId] = useState(null);
  const [sourceText, setSourceText] = useState('');
  const [language, setLanguage] = useState('py3');
  const [submitMode, setSubmitMode] = useState('code'); // 'code' | 'file'
  const [sourceFile, setSourceFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [currentJudging, setCurrentJudging] = useState(null);
  const [expandedTestcaseId, setExpandedTestcaseId] = useState(null); // testcase_id of the per-testcase chip whose stdout/stderr is open
  // ``setRecentSubId`` is the only side we read; the value itself is
  // tracked elsewhere. Prefixed to opt out of no-unused-vars.
  const [, setRecentSubId] = useState(null);
  const [clars, setClars] = useState([]);
  const [clarBody, setClarBody] = useState('');

  const pollTimer = useRef(null);
  const pollStopTimer = useRef(null);

  // Which problem is open lives in the URL (?problem=K), not in component
  // state: a reload used to drop the contestant back on problem A. The label
  // rather than the id so the link is readable and survives a re-import.
  const [searchParams, setSearchParams] = useSearchParams();
  const problemParam = searchParams.get('problem');

  // Declared before the effects that call them - the rehydration effect
  // below needs both.
  const stopPolling = () => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    if (pollStopTimer.current) {
      clearTimeout(pollStopTimer.current);
      pollStopTimer.current = null;
    }
  };

  const pollJudging = (sid) => {
    stopPolling();
    const run = async () => {
      try {
        const { data } = await getJudging(sid);
        setCurrentJudging(data);
        if (data.verdict !== 'pending') stopPolling();
      } catch {
        /* keep polling briefly */
      }
    };
    run();
    pollTimer.current = setInterval(run, 800);
    // Hard stop so we don't poll forever on a wedged judge. Tracked in a ref
    // so unmounting (or switching problems) cancels it - it used to be a
    // bare setTimeout that fired into a dead component.
    pollStopTimer.current = setTimeout(stopPolling, 120000);
  };

  useEffect(() => {
    Promise.all([listIcpcProblems(contest.id), listIcpcLanguages()])
      .then(([p, l]) => {
        const list = p.data || [];
        setProblems(list);
        setLanguages(l.data || []);
        if (!list.length) return;
        const fromUrl = problemParam
          ? list.find((x) => x.label === problemParam)
          : null;
        setActiveProblemId((cur) => cur ?? (fromUrl ? fromUrl.id : list[0].id));
      })
      .catch(() => {});
    listClarifications(contest.id).then((r) => setClars(r.data || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contest.id]);

  useEffect(() => () => stopPolling(), []);

  const activeProblem = useMemo(
    () => problems.find((p) => p.id === activeProblemId) || null,
    [problems, activeProblemId],
  );

  // Keep ?problem= in step with the open problem, so a reload (or a link
  // pasted in a clarification) lands back on the same one.
  useEffect(() => {
    if (!activeProblem || problemParam === activeProblem.label) return;
    const next = new URLSearchParams(searchParams);
    next.set('problem', activeProblem.label);
    // replace, not push: 12 problems browsed = 12 useless history entries.
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProblem, problemParam]);

  // Rehydrate the judging panel for whichever problem is open. Previously
  // ``currentJudging`` was write-only component state: refreshing the page
  // mid-judging left the contestant with no way at all to see their pending
  // submission, since this view has no submission history of its own.
  useEffect(() => {
    if (!activeProblem) return undefined;
    let cancelled = false;
    stopPolling();
    /* eslint-disable react-hooks/set-state-in-effect */
    setCurrentJudging(null);
    setExpandedTestcaseId(null);
    /* eslint-enable react-hooks/set-state-in-effect */
    getMyLatestProblemSubmission(contest.id, activeProblem.id)
      .then(({ data }) => {
        const sub = (data || [])[0];
        if (cancelled || !sub) return;
        setRecentSubId(sub.id);
        if (!sub.latest_verdict || sub.latest_verdict === 'pending') {
          // Still in the queue - resume the live poll.
          pollJudging(sub.id);
        } else {
          getJudging(sub.id)
            .then((j) => { if (!cancelled) setCurrentJudging(j.data); })
            .catch(() => {});
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contest.id, activeProblem?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeProblem) return;
    const hasFile = submitMode === 'file' && sourceFile;
    const hasCode = submitMode === 'code' && sourceText.trim();
    if (!hasFile && !hasCode) {
      toast.error(t('icpc.toastSourceEmpty'));
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('language', language);
      if (selectedTeamId) fd.append('team_id', selectedTeamId);
      if (hasFile) {
        fd.append('file', sourceFile, sourceFile.name);
      } else {
        fd.append('source', sourceText);
      }
      const { data } = await submitIcpc(contest.id, activeProblem.id, fd);
      setRecentSubId(data.id);
      setCurrentJudging({ verdict: 'pending', runs: [] });
      setExpandedTestcaseId(null);
      pollJudging(data.id);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastSubmitFailed')));
    } finally {
      setSubmitting(false);
    }
  };

  // Auto-pick the language from the file extension (case-insensitive),
  // matching the Language.extensions column the backend seeds. Leaves the
  // language alone if no match - the admin may have named the file weirdly.
  const pickFile = (file) => {
    setSourceFile(file || null);
    if (!file) return;
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    const match = languages.find((l) =>
      (l.extensions || '').split(',').map((x) => x.trim().toLowerCase()).includes(ext));
    if (match) setLanguage(match.id);
  };

  const postClarification = async (e) => {
    e.preventDefault();
    if (!clarBody.trim()) return;
    try {
      await createClarification(contest.id, {
        problem_id: activeProblem ? activeProblem.id : null,
        body: clarBody.trim(),
      });
      setClarBody('');
      const r = await listClarifications(contest.id);
      setClars(r.data || []);
      toast.success(t('icpc.toastClarSent'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastClarFailed')));
    }
  };

  const submitAnswer = async (clarId, answer, visibility) => {
    if (!answer.trim()) return;
    try {
      await answerClarification(clarId, { answer: answer.trim(), visibility });
      const r = await listClarifications(contest.id);
      setClars(r.data || []);
      toast.success(t('icpc.toastClarAnswered'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastClarFailed')));
    }
  };

  const saveEdit = async (clarId, answer, visibility) => {
    try {
      await updateClarification(clarId, { answer: answer.trim(), visibility });
      const r = await listClarifications(contest.id);
      setClars(r.data || []);
      toast.success(t('icpc.toastClarUpdated'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastClarFailed')));
    }
  };

  const toggleVisibility = async (c) => {
    const next = c.visibility === 'public' ? 'private' : 'public';
    try {
      await updateClarification(c.id, { answer: '', visibility: next });
      const r = await listClarifications(contest.id);
      setClars(r.data || []);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastClarFailed')));
    }
  };

  const removeClar = async (c) => {
    const ok = await confirm({
      message: t('icpc.confirmDeleteClar'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteClarification(c.id);
      const r = await listClarifications(contest.id);
      setClars(r.data || []);
      toast.success(t('icpc.toastClarDeleted'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('icpc.toastClarFailed')));
    }
  };

  return (
    <div className="space-y-6">
      {problems.length === 0 ? (
        <div className="card p-8 text-center">
          <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3 dark:text-amber-400" />
          <p className="text-zinc-700 dark:text-zinc-300">{t('icpc.noProblems')}</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[240px_1fr] gap-4">
          {/* Problem list */}
          <aside className="card p-3 space-y-1">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2 px-2 dark:text-zinc-400">
              {t('icpc.problemsHeading')}
            </h3>
            {problems.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  // The judging panel is restored by the effect keyed on the
                  // active problem, so nothing to clear by hand here.
                  setActiveProblemId(p.id);
                  setSourceText('');
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeProblemId === p.id
                    ? 'bg-accent-600/15 text-accent-700 dark:bg-accent-600/20 dark:text-accent-300'
                    : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800/50'
                }`}
              >
                <span
                  className="w-6 h-6 rounded-full font-mono font-bold text-xs flex items-center justify-center"
                  style={{
                    background: p.color || '#a1a1aa',
                    color: textOn(p.color || '#a1a1aa'),
                  }}
                >
                  {p.label}
                </span>
                <span className="flex-1 text-left truncate">{p.name}</span>
                <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100" />
              </button>
            ))}
          </aside>

          {/* Problem view + submit */}
          <div className="space-y-4 min-w-0">
            {activeProblem && (
              <>
                <div className="card p-6">
                  <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
                    <div>
                      <h2 className="text-xl font-bold text-zinc-900 dark:text-white">
                        {activeProblem.label}. {activeProblem.name}
                      </h2>
                      {/* The problem's own limits, and nothing else: the
                          judge scales the time limit by the language's
                          time_factor, but DOMjudge does not advertise the
                          scaled figure either. It stays on the API. */}
                      <p className="text-xs text-zinc-500 mt-1 dark:text-zinc-500">
                        {t('icpc.limits', {
                          time: (activeProblem.time_limit_ms / 1000).toFixed(1),
                          mem: activeProblem.memory_limit_mb,
                        })}
                        {' · '}
                        {t('icpc.checker', { kind: activeProblem.checker_kind })}
                      </p>
                    </div>
                    {activeProblem.has_statement_pdf && (
                      <button
                        type="button"
                        // Open via a short-lived stream ticket + blob fetch so
                        // the durable session token never enters a URL. ``v``
                        // (the file mtime) still busts the browser cache after
                        // an admin replaces the PDF.
                        onClick={() =>
                          openStatementPdf(
                            contest.id,
                            activeProblem.id,
                            activeProblem.statement_pdf_version || 0,
                          ).catch(() => toast.error(t('icpcProblems.pdfOpenFailed')))
                        }
                        className="btn-secondary text-xs"
                      >
                        <FileTextIcon className="w-3.5 h-3.5 mr-1 inline" />
                        {t('icpc.statement')}
                      </button>
                    )}
                  </div>

                  {activeProblem.sample_testcases.length > 0 && (
                    <div className="mt-4 space-y-3">
                      <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                        {t('icpc.samples')}
                      </h3>
                      {activeProblem.sample_testcases.map((tc, i) => (
                        <div key={tc.id} className="grid sm:grid-cols-2 gap-2 text-xs font-mono">
                          <CopyablePre
                            label={t('icpc.sampleInput', { n: i + 1 })}
                            content={tc.input_data || ''}
                            t={t}
                          />
                          <CopyablePre
                            label={t('icpc.sampleOutput', { n: i + 1 })}
                            content={tc.expected_output || ''}
                            t={t}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {canParticipate && (
                  <form
                    onSubmit={handleSubmit}
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !submitting) {
                        e.preventDefault();
                        e.currentTarget.requestSubmit();
                      }
                    }}
                    className="card p-6 space-y-3"
                  >
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <h3 className="text-sm font-semibold text-zinc-900 flex items-center gap-2 dark:text-white">
                        <Code2 className="w-4 h-4 text-accent-500 dark:text-accent-400" />
                        {t('icpc.submitHeading')}
                      </h3>
                      <div className="inline-flex rounded-lg border border-zinc-200 p-0.5 dark:border-zinc-700">
                        <button
                          type="button"
                          onClick={() => setSubmitMode('code')}
                          className={`text-xs font-medium px-3 py-1 rounded-md flex items-center gap-1 transition-colors ${
                            submitMode === 'code'
                              ? 'bg-accent-600 text-white'
                              : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                          }`}
                        >
                          <Code2 className="w-3.5 h-3.5" />
                          {t('icpc.modeCode')}
                        </button>
                        <button
                          type="button"
                          onClick={() => setSubmitMode('file')}
                          className={`text-xs font-medium px-3 py-1 rounded-md flex items-center gap-1 transition-colors ${
                            submitMode === 'file'
                              ? 'bg-accent-600 text-white'
                              : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                          }`}
                        >
                          <FileTextIcon className="w-3.5 h-3.5" />
                          {t('icpc.modeFile')}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <label className="text-xs text-zinc-600 dark:text-zinc-400">
                        {t('icpc.language')}
                      </label>
                      <select
                        className="input-field text-sm py-1.5 w-48"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                      >
                        {languages.map((l) => (
                          <option key={l.id} value={l.id}>{l.display_name}</option>
                        ))}
                      </select>
                      {submitMode === 'file' && sourceFile && (
                        <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                          {t('icpc.autoDetectedLang')}
                        </span>
                      )}
                    </div>
                    {submitMode === 'code' ? (
                      <div className="rounded-lg border border-zinc-300 overflow-hidden dark:border-zinc-700">
                        <CodeMirror
                          value={sourceText}
                          onChange={(v) => setSourceText(v)}
                          extensions={[python()]}
                          basicSetup={{ lineNumbers: true, highlightActiveLine: false }}
                          theme={theme === 'dark' ? oneDark : 'light'}
                          height="280px"
                        />
                      </div>
                    ) : (
                      <div className="rounded-lg border-2 border-dashed border-zinc-300 p-4 dark:border-zinc-700">
                        <input
                          type="file"
                          accept={languages.map((l) => (l.extensions || '').split(',').map((x) => '.' + x.trim()).join(',')).join(',')}
                          onChange={(e) => pickFile(e.target.files?.[0] || null)}
                          className="input-field text-sm py-2 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-accent-600 file:text-white"
                        />
                        {sourceFile && (
                          <p className="text-xs text-zinc-600 mt-2 dark:text-zinc-300">
                            {t('icpc.selectedFile', {
                              name: sourceFile.name,
                              size: Math.round(sourceFile.size / 1024),
                            })}
                          </p>
                        )}
                        <p className="text-[11px] text-zinc-400 mt-2 dark:text-zinc-500">
                          {t('icpc.fileModeHint')}
                        </p>
                      </div>
                    )}
                    <div className="flex items-center gap-3 flex-wrap">
                      <button type="submit" className="btn-primary" disabled={submitting}>
                        <Upload className="w-4 h-4 mr-2 inline" />
                        {submitting ? t('icpc.submitting') : t('icpc.submit')}
                      </button>
                      <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                        {t('contest.submitShortcutHint')}
                      </span>
                    </div>
                  </form>
                )}

                {currentJudging && (
                  <div className="card p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${VERDICT_STYLE[currentJudging.verdict] || VERDICT_STYLE.pending}`}>
                        {currentJudging.verdict === 'pending' ? (
                          <>
                            <Clock className="w-3 h-3 mr-1" />
                            {t('icpc.verdictPending')}
                          </>
                        ) : currentJudging.verdict === 'AC' ? (
                          <>
                            <CheckCircle className="w-3 h-3 mr-1" />
                            AC
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3 mr-1" />
                            {currentJudging.verdict}
                          </>
                        )}
                      </span>
                      {/* CPU time is what the limit was checked against;
                          wall clock is shown next to it but carries
                          interpreter + container startup. */}
                      {currentJudging.max_cpu_ms ? (
                        <span
                          className="text-xs text-zinc-600 font-mono tabular-nums dark:text-zinc-300"
                          title={t('icpc.cpuVsWallHint')}
                        >
                          {t('icpc.maxCpu', { ms: currentJudging.max_cpu_ms })}
                        </span>
                      ) : null}
                      {currentJudging.max_runtime_ms ? (
                        <span
                          className="text-xs text-zinc-500 dark:text-zinc-400"
                          title={t('icpc.cpuVsWallHint')}
                        >
                          {t('icpc.maxRuntime', { ms: currentJudging.max_runtime_ms })}
                        </span>
                      ) : null}
                    </div>
                    {currentJudging.compile_output && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-zinc-500 dark:text-zinc-400">
                          {t('icpc.compileOutput')}
                        </summary>
                        <pre className="mt-2 p-2 bg-zinc-50 border border-zinc-200 rounded whitespace-pre-wrap dark:bg-zinc-800/40 dark:border-zinc-700/40">
                          {currentJudging.compile_output}
                        </pre>
                      </details>
                    )}
                    {(() => {
                      const runs = currentJudging.runs || [];
                      const allTcs = currentJudging.all_testcases || [];
                      // Only render the grid once the judge has started
                      // producing runs (or finished without any - e.g. CE).
                      // Pending + no runs = the worker hasn't picked up the
                      // job yet; the spinner above already covers that.
                      const judgingStarted = runs.length > 0 || currentJudging.verdict !== 'pending';
                      if (!judgingStarted) return null;
                      // Match runs to testcases by id; fall back to a
                      // run-only listing if all_testcases is missing (older
                      // backend response).
                      const runByTc = new Map(runs.map((r) => [r.testcase_id, r]));
                      const cells = allTcs.length > 0
                        ? allTcs.map((tc, idx) => ({
                            tc, run: runByTc.get(tc.id) || null,
                            n: idx + 1, isSample: tc.is_sample,
                          }))
                        : runs.map((r, idx) => ({
                            tc: { id: r.testcase_id }, run: r,
                            n: idx + 1, isSample: r.is_sample,
                          }));
                      return (
                        <>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {cells.map(({ tc, run, n, isSample }) => {
                              const verdict = run?.verdict || 'unknown';
                              // Always clickable for failed sample tests so
                              // the user can see the expected output even if
                              // their program wrote nothing. For secret
                              // tests, require actual program output. Cells
                              // that never ran have nothing to expand.
                              const hasDetail = !!run && (run.stdout_truncated || run.stderr_truncated || (run.is_sample && run.verdict !== 'AC'));
                              const isOpen = expandedTestcaseId === tc.id;
                              return (
                                <button
                                  key={tc.id}
                                  type="button"
                                  disabled={!hasDetail}
                                  onClick={() => setExpandedTestcaseId(isOpen ? null : tc.id)}
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors ${
                                    VERDICT_STYLE[verdict] || VERDICT_STYLE.pending
                                  } ${hasDetail ? 'hover:ring-2 hover:ring-accent-400/50 cursor-pointer' : 'cursor-default'} ${
                                    isOpen ? 'ring-2 ring-accent-500' : ''
                                  }`}
                                  title={
                                    !run
                                      ? `${isSample ? 'sample' : 'secret'} #${n} · ${t('icpc.notEvaluated')}`
                                      : hasDetail
                                        ? t('icpc.clickForDetail', { kind: isSample ? 'sample' : 'secret', n, ms: runMs(run) })
                                        : `${isSample ? 'sample' : 'secret'} #${n} · ${runMs(run)} ms`
                                  }
                                >
                                  {n}: {run ? verdict : '?'}
                                </button>
                              );
                            })}
                          </div>
                          {expandedTestcaseId !== null && runByTc.get(expandedTestcaseId) && (
                            (() => {
                              const r = runByTc.get(expandedTestcaseId);
                              const cellIdx = cells.findIndex((c) => c.tc.id === expandedTestcaseId);
                              // For sample testcases only, pull the expected
                              // output from the problem payload so the user
                              // can compare their stdout side-by-side. Never
                              // leak secret-testcase expected outputs.
                              const sample = r.is_sample
                                ? (activeProblem.sample_testcases || []).find((s) => s.id === r.testcase_id)
                                : null;
                              const showCompare = sample && r.verdict !== 'AC';
                              return (
                                <div className="mt-3 space-y-2 text-xs">
                                  <p className="font-semibold text-zinc-700 dark:text-zinc-300">
                                    {t('icpc.runDetailHeader', {
                                      kind: r.is_sample ? t('icpc.sampleKind') : t('icpc.secretKind'),
                                      n: cellIdx + 1,
                                      verdict: r.verdict,
                                      ms: runMs(r),
                                    })}
                                  </p>
                                {showCompare ? (
                                  <div className="grid sm:grid-cols-2 gap-2">
                                    <div>
                                      <p className="text-[10px] uppercase text-emerald-600 dark:text-emerald-400 mb-1">
                                        {t('icpc.expectedOutput')}
                                      </p>
                                      <pre className="p-2 bg-emerald-500/5 border border-emerald-500/30 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-emerald-500/10">
                                        {sample.expected_output || '(empty)'}
                                      </pre>
                                    </div>
                                    <div>
                                      <p className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
                                        {t('icpc.yourOutput')}
                                      </p>
                                      <pre className="p-2 bg-zinc-50 border border-zinc-200 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-zinc-800/40 dark:border-zinc-700/40">
                                        {r.stdout_truncated || '(empty)'}
                                      </pre>
                                    </div>
                                  </div>
                                ) : (
                                  r.stdout_truncated && (
                                    <div>
                                      <p className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
                                        {t('icpc.stdout')}
                                      </p>
                                      <pre className="p-2 bg-zinc-50 border border-zinc-200 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-zinc-800/40 dark:border-zinc-700/40">
                                        {r.stdout_truncated}
                                      </pre>
                                    </div>
                                  )
                                )}
                                {r.stderr_truncated && (
                                  <div>
                                    <p className="text-[10px] uppercase text-red-600 dark:text-red-400 mb-1">
                                      {t('icpc.stderr')}
                                    </p>
                                    <pre className="p-2 bg-red-500/5 border border-red-500/30 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-red-500/10">
                                      {r.stderr_truncated}
                                    </pre>
                                  </div>
                                )}
                                {!r.stdout_truncated && !r.stderr_truncated && !showCompare && (
                                  <p className="text-zinc-400 italic dark:text-zinc-600">
                                    {t('icpc.noProgramOutput')}
                                  </p>
                                )}
                              </div>
                            );
                          })()
                        )}
                      </>
                    );
                    })()}
                  </div>
                )}
              </>
            )}

            {/* Clarifications */}
            <div className="card p-4">
              <h3 className="text-sm font-semibold text-zinc-900 mb-3 flex items-center gap-2 dark:text-white">
                <MessageCircle className="w-4 h-4 text-sky-500 dark:text-sky-400" />
                {t('icpc.clarifications')}
              </h3>
              {canParticipate && (
                <form onSubmit={postClarification} className="space-y-2 mb-3">
                  <textarea
                    className="input-field text-sm py-2 min-h-[60px]"
                    placeholder={t('icpc.askPlaceholder')}
                    value={clarBody}
                    onChange={(e) => setClarBody(e.target.value)}
                  />
                  <button type="submit" className="btn-secondary text-xs" disabled={!clarBody.trim()}>
                    {t('icpc.askSubmit')}
                  </button>
                </form>
              )}
              {clars.length === 0 ? (
                <p className="text-xs text-zinc-400 italic dark:text-zinc-600">{t('icpc.noClarifications')}</p>
              ) : (
                <ul className="space-y-2 max-h-80 overflow-y-auto">
                  {clars.map((c) => (
                    <li key={c.id} className="text-xs rounded border border-zinc-200 p-2 dark:border-zinc-700/40">
                      <p className="text-zinc-700 whitespace-pre-wrap dark:text-zinc-300">
                        {c.problem_label ? <span className="font-mono mr-2">[{c.problem_label}]</span> : null}
                        {c.body}
                      </p>
                      {c.answer ? (
                        <AnsweredBlock
                          c={c}
                          isAdmin={!!user?.is_admin}
                          onSave={saveEdit}
                          onToggle={toggleVisibility}
                          onRemove={removeClar}
                          t={t}
                        />
                      ) : (
                        <p className="text-[10px] text-zinc-400 mt-1 dark:text-zinc-500">
                          {t('icpc.clarPending')}
                        </p>
                      )}
                      {user?.is_admin && !c.answer && (
                        <AdminAnswerForm clarId={c.id} onSubmit={submitAnswer} t={t} />
                      )}
                      {user?.is_admin && (
                        <div className="mt-1.5 flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => removeClar(c)}
                            className="text-[10px] text-red-600 hover:underline dark:text-red-400"
                          >
                            {t('icpc.clarDelete')}
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function CopyablePre({ label, content, t }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error(t('common.copyFailed'));
    }
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] uppercase text-zinc-400 dark:text-zinc-500">{label}</p>
        <button
          type="button"
          onClick={copy}
          className="p-1 rounded hover:bg-zinc-200 text-zinc-400 hover:text-zinc-700 transition-colors dark:hover:bg-zinc-700/50 dark:text-zinc-500 dark:hover:text-zinc-200"
          title={t('common.copy')}
          aria-label={t('common.copy')}
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="bg-zinc-50 border border-zinc-200 p-2 rounded whitespace-pre-wrap dark:bg-zinc-800/40 dark:border-zinc-700/40">
        {content}
      </pre>
    </div>
  );
}


function AnsweredBlock({ c, isAdmin, onSave, onToggle, t }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(c.answer || '');
  const [vis, setVis] = useState(c.visibility);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setText(c.answer || '');
    setVis(c.visibility);
  }, [c.answer, c.visibility]);

  const submit = async () => {
    if (!text.trim()) return;
    setSaving(true);
    try {
      await onSave(c.id, text, vis);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-1.5 pl-2 border-l-2 border-emerald-500/40">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] uppercase text-emerald-600 dark:text-emerald-400">
          {c.visibility === 'public' ? t('icpc.jurypublic') : t('icpc.juryprivate')}
        </p>
        {isAdmin && (
          <div className="inline-flex items-center gap-2 text-[10px]">
            <button
              type="button"
              onClick={() => onToggle(c)}
              className="text-sky-600 hover:underline dark:text-sky-400"
              title={t('icpc.clarToggleVisibilityHint')}
            >
              {c.visibility === 'public' ? t('icpc.clarMakePrivate') : t('icpc.clarMakePublic')}
            </button>
            {!editing && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="text-accent-600 hover:underline dark:text-accent-400"
              >
                {t('icpc.clarEdit')}
              </button>
            )}
          </div>
        )}
      </div>
      {editing ? (
        <div className="mt-1 space-y-1">
          <textarea
            className="input-field text-xs py-1 px-2 min-h-[40px]"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex items-center justify-end gap-2">
            <label className="inline-flex items-center gap-1 text-[10px] text-zinc-500 dark:text-zinc-400 mr-auto">
              <input
                type="checkbox"
                checked={vis === 'public'}
                onChange={(e) => setVis(e.target.checked ? 'public' : 'private')}
              />
              <span>{t('icpc.clarBroadcastToAll')}</span>
            </label>
            <button
              type="button"
              onClick={() => { setEditing(false); setText(c.answer || ''); setVis(c.visibility); }}
              className="btn-secondary text-[11px] py-1 px-2"
            >
              {t('common.cancel')}
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={saving || !text.trim()}
              className="btn-primary text-[11px] py-1 px-2"
            >
              {saving ? t('common.sending') : t('common.save')}
            </button>
          </div>
        </div>
      ) : (
        <p className="text-zinc-700 whitespace-pre-wrap dark:text-zinc-300">{c.answer}</p>
      )}
    </div>
  );
}


function AdminAnswerForm({ clarId, onSubmit, t }) {
  const [answer, setAnswer] = useState('');
  const [visibility, setVisibility] = useState('private');
  const [sending, setSending] = useState(false);

  const send = async (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    setSending(true);
    try {
      await onSubmit(clarId, answer, visibility);
      setAnswer('');
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={send} className="mt-2 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/40 space-y-1">
      <textarea
        className="input-field text-xs py-1 px-2 min-h-[40px]"
        placeholder={t('icpc.clarAnswerPlaceholder')}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
      <div className="flex items-center justify-between gap-2">
        <label className="inline-flex items-center gap-1 text-[10px] text-zinc-500 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={visibility === 'public'}
            onChange={(e) => setVisibility(e.target.checked ? 'public' : 'private')}
          />
          <span>{t('icpc.clarBroadcastToAll')}</span>
        </label>
        <button
          type="submit"
          className="btn-primary text-[11px] py-1 px-2"
          disabled={!answer.trim() || sending}
        >
          {sending ? t('common.sending') : t('icpc.clarAnswerSubmit')}
        </button>
      </div>
    </form>
  );
}
