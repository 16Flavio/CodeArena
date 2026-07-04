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
import PageHeader from '../components/PageHeader';

// Same top-3 colour pattern as IcpcScoreboard: gold / silver / bronze.
const MEDALS = [
  'text-yellow-500 dark:text-yellow-400',
  'text-zinc-400 dark:text-zinc-300',
  'text-amber-600',
];

// Points come out of 100 × (N − rank)/(N − 1) × coefficient and the
// backend rounds them to 2 decimals - show both decimals when the value
// is not integral (66.66 must read "66.66", not "66.7"), and keep
// integral values bare.
const fmtPoints = (x) => {
  const n = Number(x ?? 0);
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
};

export default function League() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [leagues, setLeagues] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null); // { league, rows }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadTick, setReloadTick] = useState(0); // bumped by the retry button

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
        if (!cancelled) {
          setLoading(false);
          toast.error(t('league.toastLoadFailed'));
        }
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch standings whenever the selected league changes. Clearing
  // `detail` up front means switching leagues shows the spinner instead
  // of the previous league's standings, and a failed fetch never leaves
  // stale data behind.
  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true);
    setError(false);
    setDetail(null);
    getLeague(selectedId)
      .then((r) => { if (!cancelled) setDetail(r.data); })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          toast.error(t('league.toastLoadFailed'));
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, reloadTick]);

  const league = detail?.league;
  const rows = detail?.rows || [];

  // Only counted events get a standings column. A finished event that is
  // not counted yet ("pending reveal") stays out: its points are frozen
  // until publication, so a column would just read as absences.
  const countedEvents = useMemo(
    () => (league?.events || []).filter((e) => e.finished && e.counted !== false),
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
      <div className="animate-fade-in">
        {/* No eyebrow here: nav.league and league.title are the same
            word, so it would just duplicate the title. */}
        <PageHeader
          title={t('league.title')}
          description={t('league.subtitle')}
        />
        <div className="card p-12 text-center">
          <Medal className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <p className="text-zinc-500 dark:text-zinc-400">{t('league.empty')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={league?.season ? `${t('nav.league')} · ${league.season}` : t('nav.league')}
        title={league ? league.name : t('league.title')}
        description={t('league.subtitle')}
        actions={leagues.length > 1 && (
          /* League picker - only shown when there is a choice to make. */
          <div className="flex items-center gap-1 flex-wrap justify-end bg-white p-1 rounded-full border border-zinc-200 dark:bg-zinc-900 dark:border-zinc-800">
            {leagues.map((l) => (
              <button
                key={l.id}
                onClick={() => setSelectedId(l.id)}
                className={`px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  selectedId === l.id
                    ? 'bg-accent-600 text-white'
                    : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800/60'
                }`}
              >
                {l.name}
                {l.season && <span className="ml-1.5 opacity-70 text-xs">{l.season}</span>}
              </button>
            ))}
          </div>
        )}
      />

      <div className="space-y-6">
      {league?.description && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{league.description}</p>
      )}

      {/* Events strip - each event links to its scoreboard. */}
      {league?.events?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3">
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
                  {/* 3 states: upcoming, finished awaiting publication
                      (reveal ceremony), finished and counted. */}
                  {ev.finished && ev.counted === false ? (
                    <span className="badge bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:text-amber-400">
                      {t('league.pendingReveal')}
                    </span>
                  ) : (
                    <span className={ev.finished ? 'badge-active' : 'badge-inactive'}>
                      {ev.finished ? t('league.finished') : t('league.upcoming')}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Load failure - distinct from "no standings yet": we never keep
          the previous league's rows around, we offer a retry instead. */}
      {error ? (
        <div className="card p-12 text-center">
          <Medal className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <p className="text-zinc-500 mb-4 dark:text-zinc-400">{t('league.loadError')}</p>
          <button
            onClick={() => setReloadTick((n) => n + 1)}
            className="btn-primary"
          >
            {t('common.retry')}
          </button>
        </div>
      ) : (
      /* Standings table - one column per counted event. The thead is
         sticky within the card's own scroll container (the card sets
         overflow for wide tables, which breaks viewport-level sticky,
         so the card scrolls vertically itself). */
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3">
          {t('league.standingsTable')}
        </h2>
        <div className="card overflow-hidden">
        <div className="overflow-auto max-h-[70vh]">
        <table className="w-full text-sm" aria-label={t('league.standingsTable')}>
          <thead className="sticky top-0 z-10">
            <tr className="bg-zinc-50 dark:bg-zinc-900">
              <th scope="col" className="text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('league.colRank')}</th>
              <th scope="col" className="text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('league.colPlayer')}</th>
              <th scope="col" className="text-right text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('league.colTotal')}</th>
              <th scope="col" className="text-right text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('league.colWins')}</th>
              <th scope="col" className="text-right text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800">{t('league.colPlayed')}</th>
              {countedEvents.map((ev) => (
                <th
                  key={ev.id}
                  scope="col"
                  className="text-right text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 py-3 px-3 border-b border-zinc-200 dark:border-zinc-800 min-w-[90px] max-w-[140px] truncate"
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
                  className={`border-t border-zinc-100 dark:border-zinc-800/30 transition-colors ${
                    isMe
                      ? 'bg-accent-500/10 hover:bg-accent-500/15'
                      : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/40'
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
                  {countedEvents.map((ev) => {
                    const pe = perEvent[ev.id];
                    // null rank = did not take part → 0 points, shown as
                    // a dash so absences read differently from a genuine
                    // last-place 0. The sr-only span carries the meaning
                    // for screen readers (a title tooltip alone is not
                    // reliably announced).
                    if (!pe || pe.rank == null) {
                      return (
                        <td
                          key={ev.id}
                          className="py-2 px-3 text-right text-zinc-300 dark:text-zinc-700"
                          title={t('league.absentTooltip')}
                        >
                          <span aria-hidden="true">-</span>
                          <span className="sr-only">{t('league.absentTooltip')}</span>
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
                  colSpan={5 + countedEvents.length}
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
      </div>
      )}
      </div>
    </div>
  );
}
