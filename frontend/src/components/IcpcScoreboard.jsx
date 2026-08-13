import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  RefreshCw, CheckCircle, Snowflake, FileSpreadsheet, Sparkles, Trophy, AlertCircle,
  Clock,
} from 'lucide-react';
import { textOn } from '../utils/contrast';
import {
  getIcpcScoreboard, icpcScoreboardCsvUrl, openStatementPdf,
  getContests, getContest, getMyTeams,
} from '../api';
import useScoreboardStream from '../utils/useScoreboardStream';
import { useAuth } from '../AuthContext';
import { getToken } from '../utils/tokenStore';
import { formatDateTime, backendIsoMs } from '../utils/datetime';
import PageHeader from './PageHeader';

const MEDALS = [
  'text-yellow-500 dark:text-yellow-400',
  'text-zinc-400 dark:text-zinc-300',
  'text-amber-600',
];
const MEDAL_BG = [
  'bg-yellow-400/10 border-yellow-400/30',
  'bg-zinc-300/10 border-zinc-400/30',
  'bg-amber-600/10 border-amber-600/30',
];

export default function IcpcScoreboard({ contestId }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [contests, setContests] = useState([]);
  const [contest, setContest] = useState(null);
  const [myTeamIds, setMyTeamIds] = useState(() => new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const hasLoadedOnce = useRef(false);
  // ``now`` ticks every 30s so the admin freeze banner stays in sync
  // with the wall clock without calling Date.now() from render
  // (impurity warning under react-hooks/purity).
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const tickId = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(tickId);
  }, []);

  const fetchData = (showToast = false) => {
    getIcpcScoreboard(contestId)
      .then((r) => {
        hasLoadedOnce.current = true;
        setData(r.data);
        setError(false);
        setLastUpdate(new Date());
        if (showToast) toast.success(t('scoreboard.refreshed'));
      })
      .catch(() => {
        if (!hasLoadedOnce.current) setError(true);
        toast.error(t('scoreboard.refreshFailed'));
      })
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
    hasLoadedOnce.current = false;
    // Resetting state when the contest changes IS the intended behaviour -
    // we want the spinner + cleared data while the new contest's
    // scoreboard loads. The cascading-render warning is a generic
    // recommendation, not applicable here.
    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true);
    setError(false);
    setData(null);
    /* eslint-enable react-hooks/set-state-in-effect */
    getContests().then((r) => setContests(r.data)).catch(() => {});
    // The scoreboard payload has no freeze/end timestamps - fetch the
    // contest once for the freeze banners.
    getContest(contestId).then((r) => setContest(r.data)).catch(() => {});
    getMyTeams()
      .then((r) => setMyTeamIds(new Set(r.data.map((tm) => tm.id))))
      .catch(() => {});
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  // Live updates over SSE, with reconnect + backoff handled by the shared
  // hook (see utils/useScoreboardStream.js for why closing on error is not
  // enough on its own).
  useScoreboardStream({
    contestId,
    enabled: autoRefresh,
    onPayload: (payload) => {
      hasLoadedOnce.current = true;
      setData(payload);
      setError(false);
      setLastUpdate(new Date());
    },
    onFallbackRefresh: () => fetchData(),
  });

  // For each problem, find the team that solved it first (lowest
  // first_solve_minutes; ties broken by row order = scoreboard rank).
  // Memo so a refresh doesn't reshuffle on equal data.
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card p-12 text-center">
        <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4 dark:text-amber-400" />
        <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">
          {error ? t('scoreboard.loadFailedHeading') : t('contest.notFoundHeading')}
        </h3>
        {error && (
          <button onClick={() => fetchData(true)} className="btn-primary text-sm mt-2">
            {t('common.retry')}
          </button>
        )}
      </div>
    );
  }

  const isUserRow = (row) => (
    (row.team_id != null && myTeamIds.has(row.team_id))
    || (row.kind === 'solo' && row.team_name === user?.username)
  );

  return (
    <div className="animate-fade-in">
      {/* This component IS the whole scoreboard page for ICPC contests
          (Scoreboard.jsx returns it directly), so the PageHeader below
          renders exactly once per page. */}
      <PageHeader
        eyebrow={t('scoreboard.title')}
        title={data.contest_title}
        description={lastUpdate
          ? t('scoreboard.lastUpdate', { time: lastUpdate.toLocaleTimeString() })
          : t('icpcScoreboard.subtitle')}
        actions={(
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <div className="relative">
              <select
                className="input-field pr-10 text-sm py-2"
                value={contestId}
                onChange={(e) => navigate(`/scoreboard/${e.target.value}`)}
                aria-label={t('scoreboard.changeContest')}
              >
                {contests.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>

            <Link to={`/contests/${contestId}`} className="btn-secondary text-sm py-2 px-3">
              {t('icpcScoreboard.backToContest')}
            </Link>

            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium transition-colors ${
                autoRefresh
                  ? 'bg-emerald-500/15 text-emerald-700 border border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-400'
                  : 'bg-zinc-100 text-zinc-500 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700'
              }`}
              title={autoRefresh ? t('scoreboard.liveOn') : t('scoreboard.liveOff')}
              aria-pressed={autoRefresh}
            >
              <RefreshCw
                className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`}
                style={autoRefresh ? { animationDuration: '3s' } : {}}
              />
              {t('scoreboard.live')}
            </button>

            <button
              onClick={() => fetchData(true)}
              className="btn-secondary text-sm py-2 px-3"
              title={t('scoreboard.refresh')}
              aria-label={t('scoreboard.refresh')}
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {user?.is_admin && (
              <button
                onClick={downloadCsv}
                className="btn-secondary text-sm py-2 px-3"
                title={t('scoreboard.exportCsv')}
                aria-label={t('scoreboard.exportCsv')}
              >
                <FileSpreadsheet className="w-4 h-4" />
              </button>
            )}
            {user?.is_admin && (
              <Link
                to={`/scoreboard/${contestId}/presentation`}
                className="btn-secondary text-sm py-2 px-3 bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 border-amber-500/30 dark:text-amber-300"
                title={t('presentation.entryTooltip')}
                aria-label={t('presentation.entryTooltip')}
              >
                <Sparkles className="w-4 h-4" />
              </Link>
            )}
          </div>
        )}
      />

      <div className="space-y-6">
      {data.frozen && (
        <div className="card p-4 border border-sky-500/30 flex items-start gap-3 bg-sky-500/5">
          <Snowflake className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5 dark:text-sky-400" />
          <div className="text-sm">
            <p className="font-semibold text-zinc-900 dark:text-white">
              {t('scoreboard.frozenTitle', {
                since: contest?.freeze_scoreboard_at
                  ? t('scoreboard.frozenSince', { time: formatDateTime(contest.freeze_scoreboard_at) })
                  : '',
              })}
            </p>
            <p className="text-zinc-600 dark:text-zinc-400 mt-0.5">
              {t('scoreboard.frozenBody', {
                endPart: contest?.end_time ? ` (${formatDateTime(contest.end_time)})` : '',
              })}
            </p>
          </div>
        </div>
      )}

      {/* Admins see the live scoreboard even when the freeze would otherwise apply. */}
      {!data.frozen && contest?.freeze_scoreboard_at && user?.is_admin && (() => {
        const freezeMs = backendIsoMs(contest.freeze_scoreboard_at);
        const endMs = backendIsoMs(contest.end_time);
        const active = freezeMs <= now && (!endMs || now < endMs);
        if (!active) return null;
        return (
          <div className="card p-4 border border-amber-500/30 flex items-start gap-3 bg-amber-500/5">
            <Snowflake className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5 dark:text-amber-400" />
            <div className="text-sm">
              <p className="font-semibold text-zinc-900 dark:text-white">{t('scoreboard.adminView')}</p>
              <p className="text-zinc-600 dark:text-zinc-400 mt-0.5">
                {t('scoreboard.adminViewBody', { time: formatDateTime(contest.freeze_scoreboard_at) })}
              </p>
            </div>
          </div>
        );
      })()}

      {data.rows.length === 0 ? (
        <div className="card p-12 text-center">
          <Trophy className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('scoreboard.noSubmissions')}</h3>
          <p className="text-zinc-500 dark:text-zinc-400">{t('scoreboard.noSubmissionsBody')}</p>
          <Link to={`/contests/${contestId}`} className="btn-primary text-sm mt-4 inline-block">
            {t('scoreboard.goToContest')}
          </Link>
        </div>
      ) : (
      <div className="card overflow-hidden">
        {/* The thead is sticky within the card's own scroll container
            (the horizontal-overflow wrapper the wide ICPC table needs
            breaks viewport-level sticky). z-20 keeps it above the
            row-sticky rank/team cells. */}
        <div className="overflow-auto max-h-[75vh]">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-20">
            <tr className="bg-zinc-50 dark:bg-zinc-900">
              <th className="text-left text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-semibold py-3 px-3 border-b border-zinc-200 dark:border-zinc-800 sticky left-0 bg-zinc-50 dark:bg-zinc-900 z-10 w-12 min-w-[48px]">#</th>
              <th className="text-left text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-semibold py-3 px-3 border-b border-zinc-200 dark:border-zinc-800 sticky left-12 bg-zinc-50 dark:bg-zinc-900 z-10 max-w-[140px] sm:max-w-none">{t('icpcScoreboard.team')}</th>
              <th className="text-right text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-semibold py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('icpcScoreboard.solved')}</th>
              <th className="text-right text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-semibold py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('icpcScoreboard.penalty')}</th>
              {data.problems.map((p) => (
                <th key={p.id} className="text-center font-semibold py-3 px-2 min-w-[64px] border-b border-zinc-200 dark:border-zinc-800">
                  {/* Clicking the letter opens the statement PDF in a new
                      tab. The backend gates access (403 before contest
                      start / for non-participants), so this stays a plain
                      badge when no PDF exists. */}
                  {p.has_statement_pdf ? (
                    <button
                      type="button"
                      onClick={() => openStatementPdf(contestId, p.id, p.statement_pdf_version)}
                      className="inline-block w-6 h-6 rounded-full text-xs font-bold leading-6 cursor-pointer transition-opacity hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-accent-500"
                      style={{ background: p.color || '#a1a1aa', color: textOn(p.color || '#a1a1aa') }}
                      title={`${p.label}${p.name ? ` - ${p.name}` : ''} · ${t('icpcScoreboard.openStatement')}`}
                    >
                      {p.label}
                    </button>
                  ) : (
                    <div
                      className="inline-block w-6 h-6 rounded-full text-xs font-bold leading-6"
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
            {data.rows.map((row, idx) => {
              const mine = isUserRow(row);
              // The rank/team cells are row-sticky, so they need an opaque
              // background - the translucent accent wash used on the rest
              // of the row would let scrolled cells bleed through.
              const stickyBg = mine
                ? 'bg-accent-50 dark:bg-accent-950 group-hover:bg-accent-100 dark:group-hover:bg-accent-900'
                : 'bg-white dark:bg-zinc-900 group-hover:bg-zinc-50 dark:group-hover:bg-zinc-800';
              return (
              <tr
                key={`${row.team_id || row.team_name}-${idx}`}
                className={`group border-t border-zinc-100 dark:border-zinc-800/30 transition-colors ${
                  mine ? 'bg-accent-500/5 hover:bg-accent-500/10' : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/40'
                }`}
              >
                <td className={`py-2 px-3 font-mono tabular-nums sticky left-0 ${stickyBg} transition-colors w-12 min-w-[48px]`}>
                  {idx < 3 ? (
                    <div className={`w-6 h-6 rounded-lg flex items-center justify-center border ${MEDAL_BG[idx]}`}>
                      <span className={`font-bold text-xs ${MEDALS[idx]}`}>{idx + 1}</span>
                    </div>
                  ) : (
                    <span className="text-zinc-500 dark:text-zinc-500">{idx + 1}</span>
                  )}
                </td>
                <td className={`py-2 px-3 font-medium sticky left-12 ${stickyBg} transition-colors max-w-[140px] sm:max-w-none truncate ${
                  mine ? 'text-accent-700 dark:text-accent-300' : 'text-zinc-900 dark:text-white'
                }`}>
                  {row.team_name}
                  {mine && (
                    <span className="ml-2 text-xs text-accent-500 font-normal dark:text-accent-400">{t('scoreboard.youTag')}</span>
                  )}
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
                <td className="py-2 px-3 text-right font-mono tabular-nums font-bold text-accent-700 dark:text-accent-300">
                  {row.solved_count}
                </td>
                <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-300">
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
                          {/* First-to-solve marker: a balloon dot in the
                              problem's color (design signature; the old
                              emoji violated the no-emoji rule and painted
                              over the sticky team column when scrolled). */}
                          {isFirst && (
                            <span
                              className="absolute -top-0.5 -right-2 w-2.5 h-2.5 rounded-full ring-2 ring-white dark:ring-zinc-900"
                              aria-label={t('icpcScoreboard.firstToSolve')}
                              style={{ background: p.color || '#f59e0b' }}
                            />
                          )}
                          <CheckCircle className="w-4 h-4" />
                          <span className="text-[10px] font-mono tabular-nums">
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
                          <div className="inline-flex items-baseline gap-0.5 text-xs font-mono tabular-nums">
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
                  // Submitted, not judged yet. Deliberately a different
                  // colour from the freeze tile above: that one means "we
                  // know but won't tell you", this one means "nobody knows
                  // yet" and clears on its own within seconds.
                  if (cell.judging_pending > 0) {
                    return (
                      <td
                        key={p.id}
                        className="py-2 px-2 text-center bg-amber-400/15 ring-1 ring-amber-400/40"
                        title={t('icpcScoreboard.judgingTooltip', { n: cell.judging_pending })}
                      >
                        <div className="inline-flex flex-col items-center gap-0.5">
                          <Clock className="w-3 h-3 text-amber-600 animate-pulse dark:text-amber-400" />
                          <div className="inline-flex items-baseline gap-0.5 text-xs font-mono tabular-nums">
                            {cell.attempts > 0 && (
                              <span className="text-red-500 dark:text-red-400">
                                {cell.attempts}
                              </span>
                            )}
                            {cell.attempts > 0 && (
                              <span className="text-zinc-500 dark:text-zinc-400">+</span>
                            )}
                            <span className="font-semibold text-amber-700 dark:text-amber-300">
                              {cell.judging_pending}
                            </span>
                          </div>
                        </div>
                      </td>
                    );
                  }
                  return (
                    <td key={p.id} className="py-2 px-2 text-center text-red-500 dark:text-red-400">
                      <span className="text-xs font-mono tabular-nums">
                        {t('icpcScoreboard.wrongAttempts', { n: cell.attempts })}
                      </span>
                    </td>
                  );
                })}
              </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>
      )}
      </div>
    </div>
  );
}
