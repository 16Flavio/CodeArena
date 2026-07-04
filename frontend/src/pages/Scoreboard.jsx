import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { getScoreboard, getContests, getContest, scoreboardStreamUrl, scoreboardCsvUrl, getStreamTicket } from '../api';
import IcpcScoreboard from '../components/IcpcScoreboard';
import {
  Trophy, ArrowUpDown, RefreshCw, Users, AlertCircle, Snowflake, FileSpreadsheet, X, Medal, Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { formatScore, formatScoreFull, clampRatio } from '../utils/format';
import { formatDateTime, backendIsoMs } from '../utils/datetime';
import { getToken } from '../utils/tokenStore';

const MEDALS = ['text-yellow-500 dark:text-yellow-400', 'text-zinc-400 dark:text-zinc-300', 'text-amber-600'];
const MEDAL_BG = [
  'bg-yellow-400/10 border-yellow-400/30',
  'bg-zinc-300/10 border-zinc-400/30',
  'bg-amber-600/10 border-amber-600/30',
];

export default function Scoreboard() {
  const { id } = useParams();
  const [kindProbe, setKindProbe] = useState(undefined);

  useEffect(() => {
    getContest(id)
      .then((r) => setKindProbe(r.data?.kind || 'output'))
      .catch(() => setKindProbe('output'));
  }, [id]);

  if (kindProbe === undefined) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (kindProbe === 'icpc') {
    return <IcpcScoreboard contestId={id} />;
  }

  return <OutputScoreboard />;
}


function OutputScoreboard() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [contests, setContests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sortBy, setSortBy] = useState('total');
  const [sortDir, setSortDir] = useState('desc');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const prevScores = useRef({});
  const hasLoadedOnce = useRef(false);
  const [flashTeams, setFlashTeams] = useState(new Set());
  const [drilldown, setDrilldown] = useState(null); // { instance, rows }
  // ``now`` ticks every 30s so the admin freeze banner stays in sync
  // with the wall clock without calling Date.now() from render
  // (impurity warning under react-hooks/purity).
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const tickId = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(tickId);
  }, []);

  const fetchData = (showToast = false) => {
    getScoreboard(id)
      .then((r) => {
        if (hasLoadedOnce.current) {
          const changed = new Set();
          r.data.teams.forEach((team) => {
            const prevTotal = prevScores.current[team.team_id];
            if (prevTotal !== undefined && prevTotal !== team.total_score) {
              changed.add(team.team_id);
            }
            prevScores.current[team.team_id] = team.total_score;
          });
          if (changed.size > 0) {
            setFlashTeams(changed);
            setTimeout(() => setFlashTeams(new Set()), 600);
          }
        } else {
          r.data.teams.forEach((team) => {
            prevScores.current[team.team_id] = team.total_score;
          });
          hasLoadedOnce.current = true;
        }
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

  useEffect(() => {
    hasLoadedOnce.current = false;
    prevScores.current = {};
    // Resetting state when the id changes IS the intended behaviour -
    // we want the spinner + cleared data while the new contest's
    // scoreboard loads. The cascading-render warning is a generic
    // recommendation, not applicable here.
    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true);
    setError(false);
    setData(null);
    /* eslint-enable react-hooks/set-state-in-effect */
    getContests().then((r) => setContests(r.data)).catch(() => {});
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Prefer Server-Sent Events: the backend pushes updates on change (no
  // client-side polling). Fall back to fetchData if the EventSource errors,
  // or if autoRefresh is off (then no background refresh at all).
  useEffect(() => {
    if (!autoRefresh) return undefined;

    let source;
    let pollInterval;
    let cancelled = false;

    const onMessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        // Mimic the change-detection behavior fetchData had.
        if (hasLoadedOnce.current) {
          const changed = new Set();
          payload.teams.forEach((team) => {
            const prev = prevScores.current[team.team_id];
            if (prev !== undefined && prev !== team.total_score) changed.add(team.team_id);
            prevScores.current[team.team_id] = team.total_score;
          });
          if (changed.size > 0) {
            setFlashTeams(changed);
            setTimeout(() => setFlashTeams(new Set()), 600);
          }
        } else {
          payload.teams.forEach((team) => {
            prevScores.current[team.team_id] = team.total_score;
          });
          hasLoadedOnce.current = true;
        }
        setData(payload);
        setError(false);
        setLastUpdate(new Date());
      } catch {
        /* malformed event; ignore */
      }
    };

    // Fetch a short-lived stream ticket (sent with the normal Bearer header)
    // and open the EventSource with that instead of the long-lived session
    // token - EventSource can't set headers, so the ticket is the only thing
    // that lands in the URL, and it expires in ~60s.
    getStreamTicket()
      .then((r) => {
        if (cancelled) return;
        const ticket = r.data.ticket;
        const url = `${scoreboardStreamUrl(id)}?token=${encodeURIComponent(ticket)}`;
        source = new EventSource(url, { withCredentials: false });
        source.onmessage = onMessage;
        source.onerror = () => {
          // Server closed the stream or the ticket expired. Fall back to one
          // refresh via the normal GET so the UI doesn't stall.
          source.close();
          if (!cancelled) fetchData();
        };
      })
      .catch(() => {
        if (cancelled) return;
        // No EventSource / couldn't get a ticket - degrade to polling.
        fetchData();
        pollInterval = setInterval(() => fetchData(), 10000);
      });

    return () => {
      cancelled = true;
      if (source) source.close();
      if (pollInterval) clearInterval(pollInterval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, id]);

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
  };

  const openDrilldown = (inst) => {
    if (!data) return;
    const rows = data.teams
      .map((tm) => {
        const s = tm.scores[String(inst.id)];
        return s && s.submission_count > 0
          ? { team: tm, best: s.best_score, subs: s.submission_count }
          : null;
      })
      .filter(Boolean)
      .sort((a, b) => b.best - a.best);
    setDrilldown({ instance: inst, rows });
  };

  const downloadCsv = () => {
    const token = getToken() || '';
    const a = document.createElement('a');
    a.href = `${scoreboardCsvUrl(id)}?_=${Date.now()}`;
    // We can't set Authorization on a link click; fetch + blob route goes through axios.
    fetch(a.href, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `scoreboard-${id}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.error(t('scoreboard.exportCsvFailed')));
  };

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

  const sortedTeams = [...data.teams].sort((a, b) => {
    let va;
    let vb;
    if (sortBy === 'total') {
      va = a.total_score;
      vb = b.total_score;
    } else {
      va = a.scores[sortBy]?.best_score || 0;
      vb = b.scores[sortBy]?.best_score || 0;
    }
    const diff = va - vb;
    return sortDir === 'desc' ? -diff : diff;
  });

  const userTeamIds = new Set();
  data.teams.forEach((team) => {
    if (team.members.includes(user?.username)) {
      userTeamIds.add(team.team_id);
    }
  });

  const maxTotal = Math.max(
    ...data.teams.map((t) => (Number.isFinite(t.total_score) ? t.total_score : 0)),
    1,
  );

  // For each instance, the best score any team achieved on it. Used to
  // compute relative progress bars + color bucketing on the per-instance cell
  // (without a static max_score we now compare against the current leader).
  const bestPerInstance = {};
  data.instances.forEach((inst) => {
    let m = 0;
    data.teams.forEach((t) => {
      const s = t.scores[String(inst.id)]?.best_score;
      if (Number.isFinite(s) && s > m) m = s;
    });
    bestPerInstance[String(inst.id)] = m;
  });

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold text-zinc-900 flex items-center gap-3 dark:text-white">
            <Trophy className="w-8 h-8 text-yellow-500 dark:text-yellow-400" />
            {t('scoreboard.title')}
          </h1>
          <p className="text-zinc-500 mt-1 truncate dark:text-zinc-400">{data.contest_title}</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <select
              className="input-field pr-10 text-sm py-2"
              value={id}
              onChange={(e) => {
                window.location.href = `/scoreboard/${e.target.value}`;
              }}
              aria-label={t('scoreboard.changeContest')}
            >
              {contests.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
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
              to={`/scoreboard/${id}/presentation`}
              className="btn-secondary text-sm py-2 px-3 bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 border-amber-500/30 dark:text-amber-300"
              title={t('presentation.entryTooltip')}
              aria-label={t('presentation.entryTooltip')}
            >
              <Sparkles className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {lastUpdate && (
        <p className="text-xs text-zinc-400 dark:text-zinc-600">
          {t('scoreboard.lastUpdate', { time: lastUpdate.toLocaleTimeString() })}
        </p>
      )}

      {data.frozen && (
        <div className="card p-4 border border-sky-500/30 flex items-start gap-3 bg-sky-500/5">
          <Snowflake className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5 dark:text-sky-400" />
          <div className="text-sm">
            <p className="font-semibold text-zinc-900 dark:text-white">
              {t('scoreboard.frozenTitle', {
                since: data.freeze_at ? t('scoreboard.frozenSince', { time: formatDateTime(data.freeze_at) }) : '',
              })}
            </p>
            <p className="text-zinc-600 dark:text-zinc-400 mt-0.5">
              {t('scoreboard.frozenBody', {
                endPart: data.end_time ? ` (${formatDateTime(data.end_time)})` : '',
              })}
            </p>
          </div>
        </div>
      )}

      {/* Admins see the live scoreboard even when the freeze would otherwise apply. */}
      {!data.frozen && data.freeze_at && user?.is_admin && (() => {
        const freezeMs = backendIsoMs(data.freeze_at);
        const endMs = backendIsoMs(data.end_time);
        const active = freezeMs <= now && (!endMs || now < endMs);
        if (!active) return null;
        return (
          <div className="card p-4 border border-amber-500/30 flex items-start gap-3 bg-amber-500/5">
            <Snowflake className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5 dark:text-amber-400" />
            <div className="text-sm">
              <p className="font-semibold text-zinc-900 dark:text-white">{t('scoreboard.adminView')}</p>
              <p className="text-zinc-600 dark:text-zinc-400 mt-0.5">
                {t('scoreboard.adminViewBody', { time: formatDateTime(data.freeze_at) })}
              </p>
            </div>
          </div>
        );
      })()}

      {sortedTeams.length === 0 ? (
        <div className="card p-12 text-center">
          <Trophy className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('scoreboard.noSubmissions')}</h3>
          <p className="text-zinc-500 dark:text-zinc-400">{t('scoreboard.noSubmissionsBody')}</p>
          <Link to={`/contests/${id}`} className="btn-primary text-sm mt-4 inline-block">
            {t('scoreboard.goToContest')}
          </Link>
        </div>
      ) : (
        <>
        {/* Mobile: per-team cards. Shows rank, team name, total + expandable per-instance mini-bars. */}
        <div className="md:hidden space-y-2">
          {sortedTeams.map((team, idx) => {
            const rank = idx + 1;
            const isUserTeam = userTeamIds.has(team.team_id);
            return (
              <div
                key={team.team_id}
                className={`card p-4 ${isUserTeam ? 'border-accent-500/40' : ''}`}
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-3 min-w-0">
                    {rank <= 3 ? (
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${MEDAL_BG[rank - 1]}`}>
                        <span className={`font-bold text-sm ${MEDALS[rank - 1]}`}>{rank}</span>
                      </div>
                    ) : (
                      <span className="text-zinc-400 font-mono pl-1 w-8 text-center dark:text-zinc-500">{rank}</span>
                    )}
                    <div className="min-w-0">
                      <p className={`font-semibold truncate ${isUserTeam ? 'text-accent-700 dark:text-accent-300' : 'text-zinc-900 dark:text-white'}`}>
                        {team.team_name}
                        {isUserTeam && <span className="ml-1 text-[11px] text-accent-500 font-normal dark:text-accent-400">{t('scoreboard.youTag')}</span>}
                      </p>
                      <p className="text-[11px] text-zinc-500 truncate dark:text-zinc-500">
                        {team.members.join(', ')}
                      </p>
                    </div>
                  </div>
                  <span className="font-mono font-bold text-base text-zinc-900 tabular-nums dark:text-white">
                    {formatScore(team.total_score)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {data.instances.map((inst) => {
                    const s = team.scores[String(inst.id)];
                    if (!s || s.submission_count === 0) {
                      return (
                        <div key={inst.id} className="text-[10px] text-zinc-400 px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-800/30 dark:text-zinc-600 truncate">
                          {inst.name}: -
                        </div>
                      );
                    }
                    const denom = bestPerInstance[String(inst.id)] || 1;
                    const pct = clampRatio(s.best_score, denom);
                    return (
                      <div
                        key={inst.id}
                        className="text-[10px] px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-800/30"
                        style={{ color: pct >= 0.9 ? '#22c55e' : pct >= 0.7 ? '#eab308' : pct >= 0.4 ? '#f97316' : '#ef4444' }}
                      >
                        <span className="truncate">{inst.name}: </span>
                        <span className="font-mono font-bold">{formatScore(s.best_score)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="card overflow-hidden hidden md:block">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-100/60 dark:bg-zinc-800/50">
                  <th className="text-left text-zinc-500 font-semibold py-4 px-4 w-16 dark:text-zinc-400">{t('scoreboard.tableRank')}</th>
                  <th className="text-left text-zinc-500 font-semibold py-4 px-4 dark:text-zinc-400">{t('scoreboard.tableTeam')}</th>
                  {data.instances.map((inst) => (
                    <th
                      key={inst.id}
                      className="text-center text-zinc-500 font-semibold py-4 px-3 select-none dark:text-zinc-400"
                    >
                      <div className="flex items-center justify-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleSort(String(inst.id))}
                          className="flex items-center gap-1 hover:text-accent-600 transition-colors focus:outline-none focus:text-accent-600 dark:hover:text-accent-400"
                          title={t('scoreboard.sortBy', { name: inst.name })}
                        >
                          <span className="truncate max-w-[120px]">{inst.name}</span>
                          {sortBy === String(inst.id) && (
                            <ArrowUpDown className="w-3 h-3 text-accent-500 flex-shrink-0 dark:text-accent-400" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => openDrilldown(inst)}
                          className="opacity-60 hover:opacity-100 text-accent-500 dark:text-accent-400"
                          title={t('scoreboard.drillTitle')}
                          aria-label={t('scoreboard.drillAria', { name: inst.name })}
                        >
                          <Medal className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </th>
                  ))}
                  <th
                    role="button"
                    tabIndex={0}
                    className="text-center text-zinc-500 font-semibold py-4 px-4 cursor-pointer hover:text-accent-600 transition-colors select-none focus:outline-none focus:text-accent-600 dark:text-zinc-400 dark:hover:text-accent-400 dark:focus:text-accent-400"
                    onClick={() => handleSort('total')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSort('total');
                      }
                    }}
                    title={t('scoreboard.sortByTotal')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      {t('scoreboard.tableTotal')}
                      {sortBy === 'total' && (
                        <ArrowUpDown className="w-3 h-3 text-accent-500 dark:text-accent-400" />
                      )}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedTeams.map((team, idx) => {
                  const isUserTeam = userTeamIds.has(team.team_id);
                  const isFlashing = flashTeams.has(team.team_id);
                  const rank = idx + 1;

                  return (
                    <tr
                      key={team.team_id}
                      className={`
                        border-t border-zinc-100 transition-all duration-300 dark:border-zinc-800/30
                        ${isUserTeam
                          ? 'bg-accent-500/5 hover:bg-accent-500/10'
                          : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/30'}
                        ${isFlashing ? 'animate-score-flash' : ''}
                      `}
                    >
                      <td className="py-4 px-4">
                        {rank <= 3 ? (
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${MEDAL_BG[rank - 1]}`}>
                            <span className={`font-bold ${MEDALS[rank - 1]}`}>{rank}</span>
                          </div>
                        ) : (
                          <span className="text-zinc-400 font-mono pl-2 dark:text-zinc-500">{rank}</span>
                        )}
                      </td>

                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="min-w-0">
                            <p className={`font-semibold truncate ${isUserTeam ? 'text-accent-700 dark:text-accent-300' : 'text-zinc-900 dark:text-white'}`}>
                              {team.team_name}
                              {isUserTeam && (
                                <span className="ml-2 text-xs text-accent-500 font-normal dark:text-accent-400">{t('scoreboard.youTag')}</span>
                              )}
                            </p>
                            <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1 truncate dark:text-zinc-500">
                              <Users className="w-3 h-3 flex-shrink-0" />
                              <span className="truncate">{team.members.join(', ')}</span>
                            </p>
                          </div>
                        </div>
                      </td>

                      {data.instances.map((inst) => {
                        const score = team.scores[String(inst.id)];
                        const pct = score
                          ? clampRatio(score.best_score, bestPerInstance[String(inst.id)] || 1)
                          : 0;
                        const hasPending = !!(score && score.pending_changes > 0);
                        const hasScore = !!(score && score.submission_count > 0);
                        return (
                          <td
                            key={inst.id}
                            className={`py-4 px-3 text-center whitespace-nowrap ${
                              hasPending ? 'bg-sky-500/20 ring-1 ring-sky-400/40' : ''
                            }`}
                            title={hasPending ? t('scoreboard.frozenTooltip') : undefined}
                          >
                            {hasScore ? (
                              <div>
                                <span
                                  className="font-mono font-bold text-sm tabular-nums"
                                  style={{
                                    color: pct >= 0.9
                                      ? '#22c55e'
                                      : pct >= 0.7
                                      ? '#eab308'
                                      : pct >= 0.4
                                      ? '#f97316'
                                      : '#ef4444',
                                  }}
                                  title={formatScoreFull(score.best_score)}
                                >
                                  {formatScore(score.best_score)}
                                </span>
                                {hasPending && (
                                  <span className="ml-1 inline-flex items-baseline gap-0.5 text-xs font-mono text-zinc-700 dark:text-zinc-200">
                                    <span>+/-</span>
                                    <span className="font-semibold">?</span>
                                    <Snowflake className="w-3 h-3 text-sky-500 dark:text-sky-300" />
                                  </span>
                                )}
                                <div className="w-full bg-zinc-200 rounded-full h-1 mt-1.5 overflow-hidden dark:bg-zinc-800">
                                  <div
                                    className="h-1 rounded-full transition-all duration-500"
                                    style={{
                                      width: `${pct * 100}%`,
                                      backgroundColor: pct >= 0.9
                                        ? '#22c55e'
                                        : pct >= 0.7
                                        ? '#eab308'
                                        : pct >= 0.4
                                        ? '#f97316'
                                        : '#ef4444',
                                    }}
                                  />
                                </div>
                                <p className="text-[10px] text-zinc-400 mt-1 dark:text-zinc-600">
                                  {score.submission_count} {t('scoreboard.countSuffix')}
                                </p>
                              </div>
                            ) : hasPending ? (
                              <div className="inline-flex flex-col items-center gap-0.5">
                                <Snowflake className="w-3 h-3 text-sky-500 dark:text-sky-300" />
                                <span className="font-mono font-bold text-sm text-zinc-700 dark:text-zinc-200">?</span>
                              </div>
                            ) : (
                              <span className="text-zinc-300 dark:text-zinc-700">-</span>
                            )}
                          </td>
                        );
                      })}

                      <td className="py-4 px-4 text-center whitespace-nowrap">
                        <div className="flex flex-col items-center">
                          <span
                            className="font-mono font-bold text-lg text-zinc-900 tabular-nums dark:text-white"
                            title={formatScoreFull(team.total_score)}
                          >
                            {formatScore(team.total_score)}
                          </span>
                          <div className="w-20 bg-zinc-200 rounded-full h-1.5 mt-1 overflow-hidden dark:bg-zinc-800">
                            <div
                              className="h-1.5 rounded-full bg-accent-500 transition-all duration-500"
                              style={{ width: `${clampRatio(team.total_score, maxTotal) * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        </>
      )}

      {drilldown && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setDrilldown(null)}>
          <div
            className="card p-6 w-full max-w-lg animate-fade-in"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
                <Medal className="w-5 h-5 text-amber-500 dark:text-amber-400" />
                {drilldown.instance.name}
              </h2>
              <button
                onClick={() => setDrilldown(null)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
                aria-label={t('accountModal.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {drilldown.rows.length === 0 ? (
              <p className="text-zinc-500 text-sm text-center py-6 dark:text-zinc-400">
                {t('scoreboard.drillEmpty')}
              </p>
            ) : (
              <ol className="space-y-1.5 max-h-[60vh] overflow-y-auto">
                {drilldown.rows.slice(0, 25).map((row, idx) => (
                  <li
                    key={row.team.team_id}
                    className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="font-mono text-sm font-bold text-zinc-400 w-6 text-right dark:text-zinc-500">
                        {idx + 1}
                      </span>
                      <span className="text-sm font-medium text-zinc-900 truncate dark:text-white">
                        {row.team.team_name}
                      </span>
                    </div>
                    <span className="font-mono font-bold text-sm text-accent-700 tabular-nums dark:text-accent-300">
                      {formatScore(row.best)}
                      <span className="text-[10px] text-zinc-400 ml-2 dark:text-zinc-500">
                        {row.subs} {t('scoreboard.countSuffix')}
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
