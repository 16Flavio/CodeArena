import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Inbox, RefreshCw, Eye, FlaskConical, Shield, Trash2, X, FileText,
} from 'lucide-react';
import {
  adminListSubmissions, adminGetSubmissionContent, overrideJudging,
  adminDeleteSubmission, adminSubmissionsStats, rejudgeSubmission, getJudging,
  overrideSubmissionScore,
} from '../../api';
import { formatDateTime } from '../../utils/datetime';
import { useConfirm, usePrompt } from '../Confirm';
import { extractErrorMessage } from '../../utils/apiError';

// Self-contained submissions browser with its own list/filter/modals
// state. Receives ``contests`` for the contest dropdown - Admin.jsx
// already has them loaded for other tabs.
export default function SubmissionsTab({ contests }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const prompt = usePrompt();

  const [list, setList] = useState({ items: [], total: 0, limit: 50, offset: 0 });
  const [filterContest, setFilterContest] = useState('');
  const [kind, setKind] = useState('output');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [viewer, setViewer] = useState(null); // { id, filename, content }
  const [viewerLoading, setViewerLoading] = useState(false);
  const [judgingViewer, setJudgingViewer] = useState(null);
  const [judgingLoading, setJudgingLoading] = useState(false);

  const load = async (offset = 0) => {
    setLoading(true);
    try {
      const params = { limit: 50, offset, kind };
      if (filterContest) params.contest_id = parseInt(filterContest, 10);
      const { data } = await adminListSubmissions(params);
      setList(data);
      const statsParams = {};
      if (filterContest) statsParams.contest_id = parseInt(filterContest, 10);
      const { data: st } = await adminSubmissionsStats(statsParams);
      setStats(st);
    } catch {
      toast.error(t('admin.submissions.toastLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Loading on (re)mount and on filter change is intentional - the
    // setState inside ``load`` is the whole point.
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterContest, kind]);

  const openContent = async (s) => {
    setViewerLoading(true);
    setViewer({ id: s.id, filename: s.file_name, content: '' });
    try {
      const { data } = await adminGetSubmissionContent(s.id);
      setViewer({ id: s.id, filename: s.file_name, content: typeof data === 'string' ? data : JSON.stringify(data) });
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.submissions.toastLoadContentFailed')));
      setViewer(null);
    } finally {
      setViewerLoading(false);
    }
  };

  const openJudgingDetail = async (s) => {
    setJudgingLoading(true);
    setJudgingViewer({ submission: s, judging: null });
    try {
      const { data } = await getJudging(s.id);
      setJudgingViewer({ submission: s, judging: data });
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
      setJudgingViewer(null);
    } finally {
      setJudgingLoading(false);
    }
  };

  const handleOverride = async (s) => {
    const verdict = await prompt({
      message: t('admin.submissions.overridePromptVerdict', { current: s.latest_verdict || '?' }),
      defaultValue: '',
    });
    if (!verdict) return;
    const reason = await prompt({
      message: t('admin.submissions.overridePromptReason'),
      defaultValue: '',
    }) || '';
    try {
      await overrideJudging(s.latest_judging_id, { verdict: verdict.toUpperCase(), reason });
      toast.success(t('admin.submissions.overrideToastOk'));
      setTimeout(() => load(list.offset), 300);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  // Output-contest counterpart of handleOverride: force a submission's
  // score. Reason is mandatory (backend rejects blank reasons - audited).
  const handleOverrideScore = async (s) => {
    const raw = await prompt({
      message: t('admin.submissions.overrideScorePromptScore', {
        current: s.score != null ? s.score.toFixed(2) : '?',
      }),
      defaultValue: '',
    });
    if (raw == null || raw === '') return;
    const score = Number(raw);
    if (!Number.isFinite(score)) {
      toast.error(t('admin.submissions.overrideScoreInvalid'));
      return;
    }
    const reason = (await prompt({
      message: t('admin.submissions.overrideScorePromptReason'),
      defaultValue: '',
    }) || '').trim();
    if (!reason) {
      toast.error(t('admin.submissions.overrideScoreReasonRequired'));
      return;
    }
    try {
      await overrideSubmissionScore(s.id, { score, reason });
      toast.success(t('admin.submissions.overrideScoreToastOk'));
      setTimeout(() => load(list.offset), 300);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const handleRejudge = async (s) => {
    const ok = await confirm({ message: t('admin.submissions.confirmRejudge', { id: s.id }) });
    if (!ok) return;
    try {
      await rejudgeSubmission(s.id);
      toast.success(t('admin.submissions.toastRejudgeQueued'));
      setTimeout(() => load(list.offset), 1500);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const handleDelete = async (s) => {
    const ok = await confirm({
      message: t('admin.submissions.confirmDelete', { id: s.id }),
      danger: true,
    });
    if (!ok) return;
    try {
      await adminDeleteSubmission(s.id);
      toast.success(t('admin.submissions.toastDeleted'));
      load(list.offset);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  return (
    <>
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-zinc-200 flex items-center justify-between flex-wrap gap-3 dark:border-zinc-800/50">
          <h3 className="text-sm font-semibold text-zinc-700 flex items-center gap-2 dark:text-zinc-300">
            <Inbox className="w-4 h-4 text-accent-500 dark:text-accent-400" />
            {t('admin.submissions.title')}
            <span className="text-xs font-normal text-zinc-400 dark:text-zinc-500">({list.total})</span>
          </h3>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-lg border border-zinc-200 p-0.5 dark:border-zinc-700">
              <button
                type="button"
                onClick={() => setKind('output')}
                className={`text-xs font-medium px-3 py-1 rounded-md transition-colors ${
                  kind === 'output'
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                }`}
              >
                {t('admin.submissions.kindOutput')}
              </button>
              <button
                type="button"
                onClick={() => setKind('icpc')}
                className={`text-xs font-medium px-3 py-1 rounded-md transition-colors ${
                  kind === 'icpc'
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200'
                }`}
              >
                {t('admin.submissions.kindIcpc')}
              </button>
            </div>
            <select
              className="input-field text-sm py-1.5"
              value={filterContest}
              onChange={(e) => setFilterContest(e.target.value)}
            >
              <option value="">{t('admin.submissions.allContests')}</option>
              {contests
                .filter((c) => (kind === 'icpc' ? c.kind === 'icpc' : c.kind !== 'icpc'))
                .map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
            </select>
            <button
              onClick={() => load(list.offset)}
              className="btn-secondary text-xs py-1.5 px-3"
              title={t('common.refresh')}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {stats && (
          <div className="px-4 py-2 border-b border-zinc-200 flex flex-wrap gap-2 text-[11px] dark:border-zinc-800/50">
            {(() => {
              const s = kind === 'icpc' ? stats.icpc : stats.output;
              const pills = [
                { k: 'total', v: s.total, cls: 'bg-zinc-500/10 text-zinc-700 dark:text-zinc-300' },
                { k: 'pending', v: s.pending, cls: 'bg-amber-500/10 text-amber-700 dark:text-amber-300' },
                { k: 'scored', v: s.scored, cls: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
                { k: 'error', v: s.error, cls: 'bg-red-500/10 text-red-700 dark:text-red-300' },
              ];
              const verdicts = kind === 'icpc' ? (stats.icpc.by_verdict || {}) : {};
              return (
                <>
                  {pills.map((p) => (
                    <span key={p.k} className={`px-2 py-0.5 rounded ${p.cls} font-mono`}>
                      {t(`admin.submissions.stat_${p.k}`)}: <strong>{p.v}</strong>
                    </span>
                  ))}
                  {Object.entries(verdicts).map(([v, n]) => (
                    <span key={v} className="px-2 py-0.5 rounded bg-accent-500/10 text-accent-700 font-mono dark:text-accent-300">
                      {v}: <strong>{n}</strong>
                    </span>
                  ))}
                </>
              );
            })()}
          </div>
        )}
        {list.items.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-10 dark:text-zinc-500">
            {loading ? t('common.loading') : t('admin.submissions.empty')}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-100/60 dark:bg-zinc-800/50">
                <tr>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">#</th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colWhen')}</th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colWho')}</th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colTeam')}</th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">
                    {kind === 'icpc' ? t('admin.submissions.colProblem') : t('admin.submissions.colInstance')}
                  </th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colFile')}</th>
                  {kind !== 'icpc' && (
                    <th className="text-right text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colScore')}</th>
                  )}
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">
                    {kind === 'icpc' ? t('admin.submissions.colVerdict') : t('admin.submissions.colStatus')}
                  </th>
                  <th className="text-right text-zinc-500 font-semibold py-2.5 px-4 dark:text-zinc-400">{t('admin.submissions.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {list.items.map((s) => (
                  <tr key={s.id} className="border-t border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800/30 dark:hover:bg-zinc-800/20">
                    <td className="py-2 px-4 font-mono text-xs text-zinc-500 dark:text-zinc-500">{s.id}</td>
                    <td className="py-2 px-4 text-xs text-zinc-500 whitespace-nowrap dark:text-zinc-400">
                      {formatDateTime(s.submitted_at)}
                    </td>
                    <td className="py-2 px-4 text-zinc-800 dark:text-zinc-200">{s.submitted_by_username}</td>
                    <td className="py-2 px-4 text-xs text-zinc-500 dark:text-zinc-400">
                      {s.team_name || <span className="italic text-zinc-400 dark:text-zinc-600">{t('admin.submissions.solo')}</span>}
                    </td>
                    <td className="py-2 px-4 text-xs text-zinc-500 dark:text-zinc-400">
                      {kind === 'icpc'
                        ? (s.problem_label || <span className="italic text-zinc-400 dark:text-zinc-600">-</span>)
                        : (s.instance_name || <span className="italic text-zinc-400 dark:text-zinc-600">-</span>)}
                    </td>
                    <td className="py-2 px-4 text-xs text-zinc-500 truncate max-w-[200px] dark:text-zinc-400" title={s.file_name}>
                      {s.file_name}
                      {s.source_language && (
                        <span className="ml-2 px-1 py-0.5 rounded bg-accent-500/10 text-accent-700 text-[10px] font-mono dark:text-accent-300">
                          {s.source_language}
                        </span>
                      )}
                    </td>
                    {kind !== 'icpc' && (
                      <td className="py-2 px-4 font-mono text-right dark:text-zinc-200">
                        {s.score != null ? s.score.toFixed(2) : '-'}
                      </td>
                    )}
                    <td className="py-2 px-4">
                      {s.latest_verdict ? (
                        <span className={
                          s.latest_verdict === 'AC'
                            ? 'badge-active'
                            : 'badge bg-red-500/15 text-red-700 border border-red-500/30 dark:text-red-300'
                        }>
                          {s.latest_verdict}
                        </span>
                      ) : (
                        <span className={
                          s.status === 'scored'
                            ? 'badge-active'
                            : s.status === 'error' || s.status === 'invalid_output'
                              ? 'badge bg-red-500/15 text-red-700 border border-red-500/30 dark:text-red-300'
                              : 'badge-inactive'
                        }>
                          {s.status}
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => openContent(s)}
                          className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-accent-500 dark:hover:bg-zinc-700/50 dark:hover:text-accent-400"
                          title={t('admin.submissions.viewContent')}
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {s.problem_id && (
                          <button
                            onClick={() => openJudgingDetail(s)}
                            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-sky-500 dark:hover:bg-zinc-700/50 dark:hover:text-sky-400"
                            title={t('admin.submissions.viewJudging')}
                          >
                            <FlaskConical className="w-4 h-4" />
                          </button>
                        )}
                        {s.problem_id && s.latest_judging_id && (
                          <button
                            onClick={() => handleOverride(s)}
                            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-emerald-500 dark:hover:bg-zinc-700/50 dark:hover:text-emerald-400"
                            title={t('admin.submissions.override')}
                          >
                            <Shield className="w-4 h-4" />
                          </button>
                        )}
                        {!s.problem_id && (
                          <button
                            onClick={() => handleOverrideScore(s)}
                            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-emerald-500 dark:hover:bg-zinc-700/50 dark:hover:text-emerald-400"
                            title={t('admin.submissions.overrideScore')}
                          >
                            <Shield className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleRejudge(s)}
                          className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-amber-500 dark:hover:bg-zinc-700/50 dark:hover:text-amber-400"
                          title={t('admin.submissions.rejudge')}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(s)}
                          className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-red-500 dark:hover:bg-zinc-700/50 dark:hover:text-red-400"
                          title={t('admin.submissions.delete')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {list.total > list.limit && (
          <div className="flex items-center justify-between p-3 border-t border-zinc-100 dark:border-zinc-800/30">
            <button
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-50"
              disabled={list.offset === 0}
              onClick={() => load(Math.max(0, list.offset - list.limit))}
            >
              {t('common.previous')}
            </button>
            <span className="text-xs text-zinc-500 dark:text-zinc-500">
              {list.offset + 1}-{Math.min(list.offset + list.limit, list.total)} / {list.total}
            </span>
            <button
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-50"
              disabled={list.offset + list.limit >= list.total}
              onClick={() => load(list.offset + list.limit)}
            >
              {t('common.next')}
            </button>
          </div>
        )}
      </div>

      {judgingViewer && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto"
          onClick={() => setJudgingViewer(null)}
        >
          <div
            className="card p-5 w-full max-w-5xl my-8"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 gap-3">
              <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
                <FlaskConical className="w-5 h-5 text-sky-500 dark:text-sky-400" />
                {t('admin.submissions.judgingTitle', { id: judgingViewer.submission.id })}
                {judgingViewer.judging && (
                  <span className={`ml-2 px-2 py-0.5 rounded font-mono text-xs ${
                    judgingViewer.judging.verdict === 'AC'
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                      : 'bg-red-500/15 text-red-700 dark:text-red-300'
                  }`}>
                    {judgingViewer.judging.verdict}
                  </span>
                )}
              </h2>
              <button
                onClick={() => setJudgingViewer(null)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 dark:hover:bg-zinc-800"
                aria-label={t('common.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {judgingLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="w-6 h-6 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : judgingViewer.judging ? (
              <div className="space-y-3">
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {t('admin.submissions.judgingMeta', {
                    when: judgingViewer.judging.judged_at ? new Date(judgingViewer.judging.judged_at).toLocaleString() : '-',
                    // CPU time when measured: that is what the limit was
                    // checked against. Wall clock otherwise.
                    ms: judgingViewer.judging.max_cpu_ms
                      ?? judgingViewer.judging.max_runtime_ms
                      ?? '-',
                  })}
                  {judgingViewer.judging.time_limit_effective_ms ? (
                    <>
                      {' · '}
                      {t('icpc.judgedAgainst', {
                        eff: (judgingViewer.judging.time_limit_effective_ms / 1000).toFixed(1),
                      })}
                    </>
                  ) : null}
                </p>
                {judgingViewer.judging.compile_output && (
                  <div>
                    <p className="text-[11px] uppercase text-zinc-500 mb-1 dark:text-zinc-400">
                      {t('icpc.compileOutput')}
                    </p>
                    <pre className="text-xs font-mono p-2 bg-zinc-500/10 border border-zinc-500/30 rounded whitespace-pre-wrap break-all max-h-60 overflow-y-auto">
                      {judgingViewer.judging.compile_output}
                    </pre>
                  </div>
                )}
                {(judgingViewer.judging.runs || []).length === 0 ? (
                  <p className="text-sm text-zinc-500 italic dark:text-zinc-500">
                    {t('admin.submissions.noRuns')}
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                    {judgingViewer.judging.runs.map((r, i) => (
                      <details
                        key={i}
                        open={r.verdict !== 'AC'}
                        className={`rounded-lg border p-2 text-xs ${
                          r.verdict === 'AC'
                            ? 'border-emerald-500/30 bg-emerald-500/5'
                            : 'border-red-500/30 bg-red-500/5'
                        }`}
                      >
                        <summary className="cursor-pointer flex items-center gap-2 font-mono">
                          <span className={`px-1.5 py-0.5 rounded font-bold ${
                            r.verdict === 'AC'
                              ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                              : 'bg-red-500/20 text-red-700 dark:text-red-300'
                          }`}>
                            {r.verdict}
                          </span>
                          <span className="text-zinc-600 dark:text-zinc-400">
                            #{i + 1} · {r.is_sample ? t('icpc.sampleKind') : t('icpc.secretKind')}
                            {' · '}
                            {r.cpu_ms != null ? `${r.cpu_ms} ms CPU` : `${r.runtime_ms || 0} ms`}
                          </span>
                        </summary>
                        {r.stderr_truncated && (
                          <div className="mt-2">
                            <p className="text-[10px] uppercase text-red-600 dark:text-red-400 mb-1">stderr</p>
                            <pre className="p-2 bg-red-500/10 border border-red-500/30 rounded font-mono whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
                              {r.stderr_truncated}
                            </pre>
                          </div>
                        )}
                        {r.stdout_truncated && (
                          <div className="mt-2">
                            <p className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">stdout</p>
                            <pre className="p-2 bg-zinc-50 border border-zinc-200 rounded font-mono whitespace-pre-wrap break-all max-h-40 overflow-y-auto dark:bg-zinc-900/40 dark:border-zinc-700/40">
                              {r.stdout_truncated}
                            </pre>
                          </div>
                        )}
                        {!r.stdout_truncated && !r.stderr_truncated && (
                          <p className="mt-2 text-zinc-400 italic dark:text-zinc-600">
                            {t('icpc.noProgramOutput')}
                          </p>
                        )}
                      </details>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {viewer && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="card p-5 w-full max-w-3xl my-8" role="dialog" aria-modal="true">
            <div className="flex items-center justify-between mb-3 gap-3">
              <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 min-w-0 dark:text-white">
                <FileText className="w-5 h-5 text-accent-500 flex-shrink-0 dark:text-accent-400" />
                <span className="truncate" title={viewer.filename}>
                  {viewer.filename || `submission_${viewer.id}.txt`}
                </span>
              </h2>
              <button
                onClick={() => setViewer(null)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 dark:hover:bg-zinc-800"
                aria-label={t('common.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {viewerLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="w-6 h-6 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <pre className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 overflow-auto max-h-[70vh] text-xs font-mono text-zinc-800 whitespace-pre-wrap dark:bg-zinc-950/40 dark:border-zinc-800 dark:text-zinc-200">
                {viewer.content || t('admin.submissions.emptyContent')}
              </pre>
            )}
          </div>
        </div>
      )}
    </>
  );
}
