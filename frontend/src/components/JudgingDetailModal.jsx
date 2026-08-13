import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X, CheckCircle, XCircle, Clock, ChevronDown, ScrollText,
} from 'lucide-react';
import { getJudging } from '../api';
import { formatDateTime } from '../utils/datetime';

// Verdict → badge classes. Mirrors the DOMjudge short codes used by
// IcpcContestView's live judging panel so the history detail and the
// live post-submit view agree visually.
const VERDICT_STYLE = {
  AC: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30 dark:text-emerald-400',
  WA: 'bg-red-500/15 text-red-700 border-red-500/30 dark:text-red-400',
  TLE: 'bg-amber-500/15 text-amber-700 border-amber-500/30 dark:text-amber-400',
  MLE: 'bg-amber-500/15 text-amber-700 border-amber-500/30 dark:text-amber-400',
  RE: 'bg-red-500/15 text-red-700 border-red-500/30 dark:text-red-400',
  RTE: 'bg-red-500/15 text-red-700 border-red-500/30 dark:text-red-400',
  CE: 'bg-zinc-500/15 text-zinc-700 border-zinc-500/30 dark:text-zinc-300',
  pending: 'bg-zinc-200 text-zinc-700 border-zinc-300 dark:bg-zinc-700 dark:text-zinc-300 dark:border-zinc-600',
  // Testcase the judge never reached (short-circuit at an earlier failure
  // or a compile error). Faded so it recedes behind the real verdicts.
  unknown: 'bg-zinc-100 text-zinc-400 border-zinc-200 dark:bg-zinc-800/40 dark:text-zinc-500 dark:border-zinc-700/40',
};

// Small color-coded verdict pill, shared with the ICPC submission-history
// tables. ``pendingLabel`` replaces the raw "pending" code with a
// translated label when the judging hasn't settled yet.
export function VerdictBadge({ verdict, pendingLabel }) {
  const v = verdict || 'pending';
  const isPending = v === 'pending';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${VERDICT_STYLE[v] || VERDICT_STYLE.pending}`}>
      {isPending ? (
        <>
          <Clock className="w-3 h-3 mr-1" />
          {pendingLabel || v}
        </>
      ) : v === 'AC' ? (
        <>
          <CheckCircle className="w-3 h-3 mr-1" />
          AC
        </>
      ) : (
        <>
          <XCircle className="w-3 h-3 mr-1" />
          {v}
        </>
      )}
    </span>
  );
}

// Modal showing the full judging detail (verdict, compile output, and the
// per-testcase runs) for one ICPC submission. Fetches through the same
// endpoint IcpcContestView polls after a submit, so secret-testcase
// output redaction is enforced server-side for non-admins.
export default function JudgingDetailModal({ submissionId, problemLabel, onClose }) {
  const { t } = useTranslation();
  const [judging, setJudging] = useState(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  // testcase_id whose stdout/stderr detail row is expanded, or null.
  const [expandedTcId, setExpandedTcId] = useState(null);

  // Parents render the modal with ``key={submissionId}``, so a different
  // submission remounts the component and the initial state above is the
  // loading state - no synchronous resets needed here.
  useEffect(() => {
    let cancelled = false;
    getJudging(submissionId)
      .then((r) => { if (!cancelled) setJudging(r.data); })
      .catch(() => { if (!cancelled) setFailed(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [submissionId]);

  // Match runs to the problem's full testcase grid by id (rank order);
  // fall back to a run-only listing if all_testcases is missing. Same
  // pairing logic as IcpcContestView's live panel.
  const runs = judging?.runs || [];
  const allTcs = judging?.all_testcases || [];
  const runByTc = new Map(runs.map((r) => [r.testcase_id, r]));
  const rows = allTcs.length > 0
    ? allTcs.map((tc, idx) => ({
        id: tc.id, n: idx + 1, isSample: !!tc.is_sample, run: runByTc.get(tc.id) || null,
      }))
    : runs.map((r, idx) => ({
        id: r.testcase_id, n: idx + 1, isSample: !!r.is_sample, run: r,
      }));

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div
        className="card p-6 w-full max-w-2xl max-h-[85vh] overflow-y-auto animate-fade-in"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
              <ScrollText className="w-5 h-5 text-accent-500 dark:text-accent-400" />
              {t('judging.title')}
            </h2>
            {problemLabel && (
              <p className="text-xs text-zinc-500 mt-0.5 truncate dark:text-zinc-400">
                {problemLabel}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
            aria-label={t('common.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <div className="w-6 h-6 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : failed ? (
          <p className="text-sm text-red-600 py-6 text-center dark:text-red-400">
            {t('judging.loadFailed')}
          </p>
        ) : judging && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <VerdictBadge verdict={judging.verdict} pendingLabel={t('icpc.verdictPending')} />
              {judging.max_cpu_ms ? (
                <span
                  className="text-xs text-zinc-600 font-mono tabular-nums dark:text-zinc-300"
                  title={t('icpc.cpuVsWallHint')}
                >
                  {t('icpc.maxCpu', { ms: judging.max_cpu_ms })}
                </span>
              ) : null}
              {judging.max_runtime_ms ? (
                <span
                  className="text-xs text-zinc-500 font-mono tabular-nums dark:text-zinc-400"
                  title={t('icpc.cpuVsWallHint')}
                >
                  {t('icpc.maxRuntime', { ms: judging.max_runtime_ms })}
                </span>
              ) : null}
              {judging.time_limit_effective_ms ? (
                <span
                  className="text-xs text-zinc-400 font-mono tabular-nums dark:text-zinc-500"
                  title={judging.language_time_factor > 1
                    ? t('icpc.factorHint', { factor: judging.language_time_factor })
                    : undefined}
                >
                  {t('icpc.judgedAgainst', {
                    eff: (judging.time_limit_effective_ms / 1000).toFixed(1),
                  })}
                </span>
              ) : null}
              {judging.judged_at && (
                <span className="text-xs text-zinc-400 font-mono tabular-nums dark:text-zinc-500">
                  {formatDateTime(judging.judged_at)}
                </span>
              )}
            </div>

            {judging.compile_output && (
              <details className="text-xs">
                <summary className="cursor-pointer text-zinc-500 dark:text-zinc-400">
                  {t('icpc.compileOutput')}
                </summary>
                <pre className="mt-2 p-2 bg-zinc-50 border border-zinc-200 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-zinc-800/40 dark:border-zinc-700/40">
                  {judging.compile_output}
                </pre>
              </details>
            )}

            {rows.length === 0 ? (
              <p className="text-sm text-zinc-400 italic dark:text-zinc-600">
                {t('judging.noRuns')}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-700/50">
                      <th className="text-left text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 pr-4 dark:text-zinc-400">{t('judging.colTest')}</th>
                      <th className="text-left text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 pr-4 dark:text-zinc-400">{t('judging.colKind')}</th>
                      <th className="text-left text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 pr-4 dark:text-zinc-400">{t('judging.colVerdict')}</th>
                      <th
                        className="text-right text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 pr-4 dark:text-zinc-400"
                        title={t('icpc.cpuVsWallHint')}
                      >
                        {t('judging.colCpu')}
                      </th>
                      <th
                        className="text-right text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 pr-4 dark:text-zinc-400"
                        title={t('icpc.cpuVsWallHint')}
                      >
                        {t('judging.colTime')}
                      </th>
                      <th className="text-right text-[11px] uppercase tracking-wide text-zinc-500 font-semibold pb-2 dark:text-zinc-400">{t('judging.colOutput')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(({ id, n, isSample, run }) => {
                      const hasOutput = !!run && (run.stdout_truncated || run.stderr_truncated);
                      const isOpen = expandedTcId === id;
                      return (
                        <TestcaseRow
                          key={id}
                          n={n}
                          isSample={isSample}
                          run={run}
                          hasOutput={hasOutput}
                          isOpen={isOpen}
                          onToggle={() => setExpandedTcId(isOpen ? null : id)}
                          t={t}
                        />
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TestcaseRow({ n, isSample, run, hasOutput, isOpen, onToggle, t }) {
  return (
    <>
      <tr className="border-b border-zinc-100 dark:border-zinc-800/30">
        <td className="py-2 pr-4 font-mono tabular-nums text-zinc-700 dark:text-zinc-300">{n}</td>
        <td className="py-2 pr-4 text-xs">
          <span className={isSample
            ? 'text-accent-700 dark:text-accent-300'
            : 'text-zinc-500 dark:text-zinc-400'}
          >
            {isSample ? t('icpc.sampleKind') : t('icpc.secretKind')}
          </span>
        </td>
        <td className="py-2 pr-4">
          {run ? (
            <VerdictBadge verdict={run.verdict} pendingLabel={t('icpc.verdictPending')} />
          ) : (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-bold font-mono ${VERDICT_STYLE.unknown}`}
              title={t('icpc.notEvaluated')}
            >
              ?
            </span>
          )}
        </td>
        {/* CPU first: it is the figure the time limit is checked against.
            Wall clock sits next to it, greyer, since it carries startup. */}
        <td className="py-2 pr-4 text-right font-mono tabular-nums text-xs text-zinc-700 dark:text-zinc-300">
          {run && run.cpu_ms != null ? `${run.cpu_ms} ms` : '-'}
        </td>
        <td className="py-2 pr-4 text-right font-mono tabular-nums text-xs text-zinc-400 dark:text-zinc-500">
          {run && run.runtime_ms != null ? `${run.runtime_ms} ms` : '-'}
        </td>
        <td className="py-2 text-right">
          {hasOutput && (
            <button
              type="button"
              onClick={onToggle}
              className="inline-flex items-center gap-1 text-xs text-accent-600 hover:underline dark:text-accent-400"
            >
              {isOpen ? t('judging.hideOutput') : t('judging.showOutput')}
              <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
          )}
        </td>
      </tr>
      {isOpen && run && (
        <tr className="border-b border-zinc-100 dark:border-zinc-800/30">
          <td colSpan={6} className="px-2 py-3 space-y-2 text-xs">
            {run.stdout_truncated && (
              <div>
                <p className="text-[10px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
                  {t('icpc.stdout')}
                </p>
                <pre className="p-2 bg-zinc-50 border border-zinc-200 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-zinc-800/40 dark:border-zinc-700/40">
                  {run.stdout_truncated}
                </pre>
              </div>
            )}
            {run.stderr_truncated && (
              <div>
                <p className="text-[10px] uppercase text-red-600 dark:text-red-400 mb-1">
                  {t('icpc.stderr')}
                </p>
                <pre className="p-2 bg-red-500/5 border border-red-500/30 rounded font-mono whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:bg-red-500/10">
                  {run.stderr_truncated}
                </pre>
              </div>
            )}
            {!run.stdout_truncated && !run.stderr_truncated && (
              <p className="text-zinc-400 italic dark:text-zinc-600">
                {t('icpc.noProgramOutput')}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
