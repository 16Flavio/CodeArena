import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Trophy, RefreshCw, CheckCircle, Snowflake, FileSpreadsheet, Sparkles } from 'lucide-react';
import { textOn } from '../utils/contrast';
import { getIcpcScoreboard, icpcScoreboardCsvUrl, openStatementPdf } from '../api';
import { useAuth } from '../AuthContext';
import { getToken } from '../utils/tokenStore';

const MEDALS = [
  'text-yellow-500 dark:text-yellow-400',
  'text-zinc-400 dark:text-zinc-300',
  'text-amber-600',
];

export default function IcpcScoreboard({ contestId }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = (showToast = false) => {
    getIcpcScoreboard(contestId)
      .then((r) => {
        setData(r.data);
        if (showToast) toast.success(t('scoreboard.refreshed'));
      })
      .catch(() => toast.error(t('scoreboard.refreshFailed')))
      .finally(() => setLoading(false));
  };

  const downloadCsv = () => {
    const token = getToken() || '';
    const url = `${icpcScoreboardCsvUrl(contestId)}?_=${Date.now()}`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.blob();
      })
      .then((blob) => {
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = `icpc-scoreboard-${contestId}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
      })
      .catch(() => toast.error(t('scoreboard.exportCsvFailed')));
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  // For each problem, find the team that solved it first (lowest
  // first_solve_minutes; ties broken by row order = scoreboard rank).
  // Memo so a 15s refresh doesn't reshuffle on equal data.
  const firstSolvers = useMemo(() => {
    if (!data) return {};
    const out = {};  // problem label -> row key (team_name + kind)
    for (const p of data.problems) {
      let best = null;
      let bestKey = null;
      for (const row of data.rows) {
        const cell = row.cells[p.label];
        if (!cell || !cell.solved || cell.first_solve_minutes == null) continue;
        if (best === null || cell.first_solve_minutes < best) {
          best = cell.first_solve_minutes;
          bestKey = `${row.team_name}:${row.kind}`;
        }
      }
      if (bestKey) out[p.label] = bestKey;
    }
    return out;
  }, [data]);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
            <Trophy className="w-6 h-6 text-amber-500" />
            {data.contest_title}
          </h1>
          <p className="text-xs text-zinc-500 mt-1 dark:text-zinc-500">
            {t('icpcScoreboard.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/contests/${contestId}`} className="btn-secondary text-sm">
            {t('icpcScoreboard.backToContest')}
          </Link>
          <button onClick={() => refresh(true)} className="btn-secondary text-sm" title={t('common.refresh')}>
            <RefreshCw className="w-4 h-4" />
          </button>
          {user?.is_admin && (
            <button
              onClick={downloadCsv}
              className="btn-secondary text-sm"
              title={t('scoreboard.exportCsv')}
              aria-label={t('scoreboard.exportCsv')}
            >
              <FileSpreadsheet className="w-4 h-4" />
            </button>
          )}
          {user?.is_admin && (
            <Link
              to={`/scoreboard/${contestId}/presentation`}
              className="btn-secondary text-sm bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 border-amber-500/30 dark:text-amber-300"
              title={t('presentation.entryTooltip')}
              aria-label={t('presentation.entryTooltip')}
            >
              <Sparkles className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-100/60 dark:bg-zinc-800/50">
            <tr>
              <th className="text-left font-semibold py-2 px-3 sticky left-0 bg-zinc-100/95 dark:bg-zinc-800/95 z-10">#</th>
              <th className="text-left font-semibold py-2 px-3 sticky left-10 bg-zinc-100/95 dark:bg-zinc-800/95 z-10 max-w-[140px] sm:max-w-none">{t('icpcScoreboard.team')}</th>
              <th className="text-right font-semibold py-2 px-3">{t('icpcScoreboard.solved')}</th>
              <th className="text-right font-semibold py-2 px-3">{t('icpcScoreboard.penalty')}</th>
              {data.problems.map((p) => (
                <th key={p.id} className="text-center font-semibold py-2 px-2 min-w-[64px]">
                  {/* Clicking the letter opens the statement PDF in a new
                      tab. The backend gates access (403 before contest
                      start / for non-participants), so this stays a plain
                      badge when no PDF exists. */}
                  {p.has_statement_pdf ? (
                    <button
                      type="button"
                      onClick={() => openStatementPdf(contestId, p.id, p.statement_pdf_version)}
                      className="inline-block w-6 h-6 rounded text-xs font-bold leading-6 cursor-pointer transition-opacity hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-accent-500"
                      style={{ background: p.color || '#a1a1aa', color: textOn(p.color || '#a1a1aa') }}
                      title={`${p.label}${p.name ? ` - ${p.name}` : ''} · ${t('icpcScoreboard.openStatement')}`}
                    >
                      {p.label}
                    </button>
                  ) : (
                    <div
                      className="inline-block w-6 h-6 rounded text-xs font-bold leading-6"
                      style={{ background: p.color || '#a1a1aa', color: textOn(p.color || '#a1a1aa') }}
                      title={p.name || p.label}
                    >
                      {p.label}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, idx) => (
              <tr
                key={`${row.team_id || row.team_name}-${idx}`}
                className="border-t border-zinc-100 dark:border-zinc-800/30"
              >
                <td className="py-2 px-3 font-mono sticky left-0 bg-white/95 dark:bg-zinc-900/95">
                  <span className={idx < 3 ? MEDALS[idx] : 'text-zinc-500 dark:text-zinc-500'}>
                    {idx + 1}
                  </span>
                </td>
                <td className="py-2 px-3 font-medium text-zinc-900 dark:text-white sticky left-10 bg-white/95 dark:bg-zinc-900/95 max-w-[140px] sm:max-w-none truncate">
                  {row.team_name}
                  {row.affiliation_name && (
                    <span
                      className="ml-2 inline-block text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                      title={row.affiliation_name}
                    >
                      {row.affiliation_name}
                    </span>
                  )}
                  {row.members.length > 1 && (
                    <span className="text-xs text-zinc-400 ml-2 dark:text-zinc-500">
                      ({row.members.join(', ')})
                    </span>
                  )}
                </td>
                <td className="py-2 px-3 text-right font-mono font-bold text-accent-700 dark:text-accent-300">
                  {row.solved_count}
                </td>
                <td className="py-2 px-3 text-right font-mono text-zinc-600 dark:text-zinc-300">
                  {row.total_penalty}
                </td>
                {data.problems.map((p) => {
                  const cell = row.cells[p.label];
                  if (!cell) {
                    return (
                      <td key={p.id} className="py-2 px-2 text-center text-zinc-300 dark:text-zinc-700">
                        -
                      </td>
                    );
                  }
                  if (cell.solved) {
                    const rowKey = `${row.team_name}:${row.kind}`;
                    const isFirst = firstSolvers[p.label] === rowKey;
                    return (
                      <td
                        key={p.id}
                        className={`py-2 px-2 text-center ${isFirst ? 'bg-amber-400/10 ring-1 ring-amber-400/40' : ''}`}
                        title={isFirst ? t('icpcScoreboard.firstToSolve') : undefined}
                      >
                        <div className="inline-flex flex-col items-center text-emerald-600 dark:text-emerald-400 relative">
                          {isFirst && (
                            <span
                              className="absolute -top-1 -right-2 text-[10px]"
                              aria-label={t('icpcScoreboard.firstToSolve')}
                              style={{ color: p.color || '#f59e0b' }}
                            >
                              🎈
                            </span>
                          )}
                          <CheckCircle className="w-4 h-4" />
                          <span className="text-[10px] font-mono">
                            {cell.first_solve_minutes ?? 0}
                          </span>
                          {cell.attempts > 1 && (
                            <span className="text-[9px] text-zinc-400 dark:text-zinc-500">
                              {t('icpcScoreboard.attemptsShort', { n: cell.attempts })}
                            </span>
                          )}
                        </div>
                      </td>
                    );
                  }
                  // Post-freeze submission on an un-solved cell - paint
                  // the whole tile blue ("frozen" look) but keep the
                  // pre-freeze wrong-attempt count in red so the viewer
                  // still sees what WAS revealed. Post-freeze attempts
                  // appear next to it in white without a verdict - the
                  // two numbers are additive in the DOMjudge style
                  // "3 + 1?".
                  if (cell.pending_attempts > 0) {
                    return (
                      <td
                        key={p.id}
                        className="py-2 px-2 text-center bg-sky-500/20 ring-1 ring-sky-400/40"
                        title={t('icpcScoreboard.frozenTooltip')}
                      >
                        <div className="inline-flex flex-col items-center gap-0.5">
                          <Snowflake className="w-3 h-3 text-sky-500 dark:text-sky-300" />
                          <div className="inline-flex items-baseline gap-0.5 text-xs font-mono">
                            {cell.attempts > 0 && (
                              <span className="text-red-500 dark:text-red-400">
                                {cell.attempts}
                              </span>
                            )}
                            {cell.attempts > 0 && (
                              <span className="text-zinc-500 dark:text-zinc-400">+</span>
                            )}
                            <span className="text-zinc-800 dark:text-white font-semibold">
                              {cell.pending_attempts}?
                            </span>
                          </div>
                        </div>
                      </td>
                    );
                  }
                  return (
                    <td key={p.id} className="py-2 px-2 text-center text-red-500 dark:text-red-400">
                      <span className="text-xs font-mono">
                        {t('icpcScoreboard.wrongAttempts', { n: cell.attempts })}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
            {data.rows.length === 0 && (
              <tr>
                <td colSpan={4 + data.problems.length} className="py-10 text-center text-zinc-400 italic dark:text-zinc-600">
                  {t('icpcScoreboard.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
