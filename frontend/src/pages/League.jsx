import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Medal, Trophy, Code, FlaskConical, Users, CalendarDays,
} from 'lucide-react';
import { listLeagues, getLeague } from '../api';
import { useAuth } from '../AuthContext';
import { formatDateTime } from '../utils/datetime';

// Same top-3 colour pattern as IcpcScoreboard: gold / silver / bronze.
const MEDALS = [
  'text-yellow-500 dark:text-yellow-400',
  'text-zinc-400 dark:text-zinc-300',
  'text-amber-600',
];

// Points come out of 100 × (N − rank)/(N − 1) × coefficient, so they're
// rarely integers — one decimal keeps columns aligned without noise.
const fmtPoints = (x) => Number(x ?? 0).toFixed(1);

export default function League() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [leagues, setLeagues] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null); // { league, rows }
  const [loading, setLoading] = useState(true);

  // Load the league list once, auto-select the first one.
  useEffect(() => {
    let cancelled = false;
    listLeagues()
      .then((r) => {
        if (cancelled) return;
        setLeagues(r.data || []);
        if (r.data?.length) setSelectedId(r.data[0].id);
        else setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
        toast.error(t('league.toastLoadFailed'));
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch standings whenever the selected league changes.
  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true);
    getLeague(selectedId)
      .then((r) => { if (!cancelled) setDetail(r.data); })
      .catch(() => toast.error(t('league.toastLoadFailed')))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const league = detail?.league;
  const rows = detail?.rows || [];

  // Only finished events get a standings column — upcoming ones exist
  // in the strip but have no points yet.
  const finishedEvents = useMemo(
    () => (league?.events || []).filter((e) => e.finished),
    [league],
  );

  if (loading && !detail) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (leagues.length === 0) {
    return (
      <div className="animate-fade-in space-y-6">
        <h1 className="text-3xl font-bold text-zinc-900 flex items-center gap-3 dark:text-white">
          <Medal className="w-8 h-8 text-accent-500" />
          {t('league.title')}
        </h1>
        <div className="card p-12 text-center">
          <Medal className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <p className="text-zinc-500 dark:text-zinc-400">{t('league.empty')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-900 flex items-center gap-3 dark:text-white">
          <Medal className="w-8 h-8 text-accent-500" />
          {league ? league.name : t('league.title')}
          {league?.season && (
            <span className="badge bg-zinc-100 text-zinc-600 border border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700">
              {league.season}
            </span>
          )}
        </h1>
        <p className="text-sm text-zinc-500 mt-1 dark:text-zinc-400">
          {t('league.subtitle')}
        </p>
      </div>

      {/* League picker — only shown when there is a choice to make. */}
      {leagues.length > 1 && (
        <div className="flex gap-1 bg-white/50 p-1 rounded-lg w-fit border border-zinc-200 dark:bg-zinc-900/50 dark:border-zinc-800/50 flex-wrap">
          {leagues.map((l) => (
            <button
              key={l.id}
              onClick={() => setSelectedId(l.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedId === l.id
                  ? 'bg-accent-600 text-white'
                  : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800/50'
              }`}
            >
              {l.name}
              {l.season && <span className="ml-1.5 opacity-70 text-xs">{l.season}</span>}
            </button>
          ))}
        </div>
      )}

      {league?.description && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{league.description}</p>
      )}

      {/* Events strip — each event links to its scoreboard. */}
      {league?.events?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 mb-2 dark:text-zinc-300">
            {t('league.events')}
          </h2>
          <div className="flex flex-wrap gap-2">
            {league.events.map((ev) => (
              <Link
                key={ev.id}
                to={`/scoreboard/${ev.contest_id}`}
                className="card-hover px-3 py-2 min-w-[190px] max-w-[260px]"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-zinc-900 truncate dark:text-white">
                    {ev.contest_title}
                  </span>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium border shrink-0 ${
                    ev.contest_kind === 'icpc'
                      ? 'bg-sky-500/15 text-sky-700 border-sky-500/30 dark:text-sky-300'
                      : 'bg-accent-500/15 text-accent-700 border-accent-500/30 dark:text-accent-300'
                  }`}>
                    {ev.contest_kind === 'icpc'
                      ? <><Code className="w-3 h-3" /> ICPC</>
                      : <><FlaskConical className="w-3 h-3" /> {t('league.kindOutput')}</>}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400 flex-wrap">
                  {ev.start_time && (
                    <span className="inline-flex items-center gap-1">
                      <CalendarDays className="w-3 h-3" />
                      {formatDateTime(ev.start_time)}
                    </span>
                  )}
                  <span
                    className="inline-flex items-center gap-1"
                    title={t('league.participants', { count: ev.participants })}
                  >
                    <Users className="w-3 h-3" />
                    <span className="font-mono tabular-nums">{ev.participants}</span>
                  </span>
                  {ev.coefficient !== 1 && (
                    <span className="badge bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:text-amber-400">
                      {t('league.coefficient', { value: ev.coefficient })}
                    </span>
                  )}
                  <span className={ev.finished ? 'badge-active' : 'badge-inactive'}>
                    {ev.finished ? t('league.finished') : t('league.upcoming')}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Standings table — one column per finished event. */}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-100/60 dark:bg-zinc-800/50">
            <tr>
              <th className="text-left font-semibold py-2 px-3">{t('league.colRank')}</th>
              <th className="text-left font-semibold py-2 px-3">{t('league.colPlayer')}</th>
              <th className="text-right font-semibold py-2 px-3">{t('league.colTotal')}</th>
              <th className="text-right font-semibold py-2 px-3">{t('league.colWins')}</th>
              <th className="text-right font-semibold py-2 px-3">{t('league.colPlayed')}</th>
              {finishedEvents.map((ev) => (
                <th
                  key={ev.id}
                  className="text-right font-semibold py-2 px-3 min-w-[90px] max-w-[140px] truncate"
                  title={ev.contest_title}
                >
                  {ev.contest_title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isMe = user?.username && row.username === user.username;
              const perEvent = Object.fromEntries(
                (row.per_event || []).map((pe) => [pe.event_id, pe]),
              );
              return (
                <tr
                  key={row.user_id}
                  className={`border-t border-zinc-100 dark:border-zinc-800/30 ${
                    isMe ? 'bg-accent-500/10' : ''
                  }`}
                >
                  <td className="py-2 px-3 font-mono tabular-nums">
                    <span className={`inline-flex items-center gap-1 ${
                      row.rank <= 3 ? MEDALS[row.rank - 1] : 'text-zinc-500 dark:text-zinc-500'
                    }`}>
                      {row.rank <= 3 && <Trophy className="w-3.5 h-3.5" />}
                      {row.rank}
                    </span>
                  </td>
                  <td className="py-2 px-3 font-medium text-zinc-900 dark:text-white whitespace-nowrap">
                    {row.username}
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums font-bold text-accent-700 dark:text-accent-300">
                    {fmtPoints(row.total_points)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-300">
                    {row.wins}
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-300">
                    {row.events_played}
                  </td>
                  {finishedEvents.map((ev) => {
                    const pe = perEvent[ev.id];
                    // null rank = did not take part → 0 points, shown as
                    // an em-dash so absences read differently from a
                    // genuine last-place 0.0.
                    if (!pe || pe.rank == null) {
                      return (
                        <td
                          key={ev.id}
                          className="py-2 px-3 text-right text-zinc-300 dark:text-zinc-700"
                          title={t('league.absentTooltip')}
                        >
                          —
                        </td>
                      );
                    }
                    return (
                      <td
                        key={ev.id}
                        className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-300"
                        title={t('league.eventRank', { rank: pe.rank })}
                      >
                        {fmtPoints(pe.points)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={5 + finishedEvents.length}
                  className="py-10 text-center text-zinc-400 italic dark:text-zinc-600"
                >
                  {t('league.noStandings')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
