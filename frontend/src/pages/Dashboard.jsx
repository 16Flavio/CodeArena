import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { getContests, getMyTeams, getMyRankings } from '../api';
import {
  Trophy, Users, Clock, ArrowRight, Target, Medal, Calendar, Sparkles, Flame,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { formatScore, formatScoreFull } from '../utils/format';
import { formatDateTime, backendIsoMs } from '../utils/datetime';

// Live countdown text: "2 j 04:12" beyond a day, "01:42:08" under it.
function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function countdown(targetMs, now) {
  const diff = Math.max(0, targetMs - now);
  const s = Math.floor(diff / 1000);
  const days = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  if (days > 0) return `${days} j ${pad(h)}:${pad(m)}`;
  return `${pad(h)}:${pad(m)}:${pad(sec)}`;
}

const MEDAL_RING = {
  1: 'border-amber-400 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40',
  2: 'border-zinc-300 text-zinc-500 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-800/60',
  3: 'border-orange-300 text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/40',
};

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [contests, setContests] = useState([]);
  const [teams, setTeams] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const now = useNow();

  useEffect(() => {
    Promise.all([getContests(), getMyTeams(), getMyRankings().catch(() => ({ data: [] }))])
      .then(([c, tm, r]) => {
        setContests(c.data);
        setTeams(tm.data);
        setRankings(r.data);
      })
      .catch(() => toast.error(t('dashboard.toastLoadFailed')))
      .finally(() => setLoading(false));
  }, []);

  // Mutually exclusive buckets: a contest in "past" never shows up in
  // "active" or "upcoming", even if practice mode keeps submissions open
  // after end_time. Order of precedence: past > active > upcoming.
  const isPast = (c) => {
    const end = backendIsoMs(c.end_time);
    return end != null && end <= now;
  };
  const pastContests = contests.filter(isPast);
  const activeContests = contests.filter((c) => !isPast(c) && c.is_open_for_submissions);
  const upcomingContests = contests
    .filter((c) => {
      if (isPast(c) || c.is_open_for_submissions) return false;
      const start = backendIsoMs(c.start_time);
      return start && start > now;
    })
    .sort((a, b) => (backendIsoMs(a.start_time) || 0) - (backendIsoMs(b.start_time) || 0));
  const myTeam = teams[0] || null;

  // The hero slot: a running contest wins; otherwise the next upcoming.
  const featured = activeContests[0] || null;
  const nextUp = !featured ? upcomingContests[0] || null : null;
  const otherActive = featured ? activeContests.slice(1) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header row: greeting left, inline counters right. */}
      <div className="flex flex-wrap items-end justify-between gap-4 pb-6 mb-8 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-accent-600 dark:text-accent-400 mb-1.5">
            {t('nav.dashboard')}
          </p>
          <h1 className="text-2xl lg:text-[28px] font-bold tracking-tight text-zinc-900 dark:text-white">
            {t('dashboard.welcome', { username: '' }).replace(',', '').trim()},{' '}
            <span className="text-accent-600 dark:text-accent-400">{user.username}</span>
          </h1>
        </div>
        <dl className="flex items-center gap-6 text-sm">
          {[
            { label: t('dashboard.activeContests'), value: activeContests.length },
            { label: t('dashboard.upcomingContests'), value: upcomingContests.length },
            { label: t('dashboard.totalContests'), value: contests.length },
          ].map((s) => (
            <div key={s.label}>
              <dt className="text-[11px] uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{s.label}</dt>
              <dd className="text-xl font-bold font-mono tabular-nums text-zinc-900 dark:text-white">{s.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 items-start">
        {/* ── Hero column ─────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-6">
          {featured ? (
            <section className="card overflow-hidden">
              <div className="px-6 pt-5 pb-4 flex items-center gap-3 border-b border-zinc-100 dark:border-zinc-800/60">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" aria-hidden />
                <p className="text-xs font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
                  {t('dashboard.happeningNow')}
                </p>
                {featured.end_time && (
                  <span className="ml-auto font-mono tabular-nums text-lg font-semibold text-zinc-900 dark:text-white" title={formatDateTime(featured.end_time)}>
                    {countdown(backendIsoMs(featured.end_time), now)}
                  </span>
                )}
              </div>
              <div className="p-6">
                <h2 className="text-xl lg:text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
                  {featured.title}
                </h2>
                {featured.description && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 line-clamp-2 max-w-2xl">
                    {featured.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400 mt-4">
                  <span className="flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5" />
                    {featured.instance_count} {t('dashboard.instances', { count: featured.instance_count })}
                  </span>
                  {featured.end_time && (
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {t('dashboard.endsOn', { date: formatDateTime(featured.end_time) })}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-6">
                  <Link to={`/contests/${featured.id}`} className="btn-primary">
                    {t('dashboard.viewContest')}
                    <ArrowRight className="w-4 h-4 ml-1.5 inline" />
                  </Link>
                  <Link to={`/scoreboard/${featured.id}`} className="btn-secondary">
                    <Trophy className="w-4 h-4 mr-1.5 inline" />
                    {t('dashboard.scoreboard')}
                  </Link>
                </div>
              </div>
            </section>
          ) : nextUp ? (
            <section className="card overflow-hidden">
              <div className="px-6 pt-5 pb-4 flex items-center gap-3 border-b border-zinc-100 dark:border-zinc-800/60">
                <Calendar className="w-4 h-4 text-sky-600 dark:text-sky-400" aria-hidden />
                <p className="text-xs font-semibold uppercase tracking-widest text-sky-600 dark:text-sky-400">
                  {t('dashboard.nextUp')}
                </p>
                {nextUp.start_time && (
                  <span className="ml-auto font-mono tabular-nums text-lg font-semibold text-zinc-900 dark:text-white" title={formatDateTime(nextUp.start_time)}>
                    {countdown(backendIsoMs(nextUp.start_time), now)}
                  </span>
                )}
              </div>
              <div className="p-6">
                <h2 className="text-xl lg:text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
                  {nextUp.title}
                </h2>
                {nextUp.description && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 line-clamp-2 max-w-2xl">
                    {nextUp.description}
                  </p>
                )}
                {nextUp.start_time && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-4 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {t('dashboard.startsOn', { date: formatDateTime(nextUp.start_time) })}
                  </p>
                )}
                <div className="mt-6">
                  <Link to={`/contests/${nextUp.id}`} className="btn-secondary">
                    {t('dashboard.view')}
                    <ArrowRight className="w-4 h-4 ml-1.5 inline" />
                  </Link>
                </div>
              </div>
            </section>
          ) : (
            <section className="card p-10 text-center">
              <Trophy className="w-10 h-10 text-zinc-300 mx-auto mb-3 dark:text-zinc-600" />
              <p className="text-zinc-600 dark:text-zinc-300 font-medium">{t('dashboard.noActiveContests')}</p>
              <p className="text-zinc-500 text-sm mt-1 dark:text-zinc-500">{t('dashboard.checkBackLater')}</p>
              <Link to="/learn" className="btn-secondary inline-flex items-center mt-5">
                {t('nav.learn')}
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Link>
            </section>
          )}

          {otherActive.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
                <Flame className="w-4 h-4" />
                {t('dashboard.activeContests')}
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {otherActive.map((contest) => (
                  <Link key={contest.id} to={`/contests/${contest.id}`} className="card-hover p-5 group">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="font-semibold text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                        {contest.title}
                      </h3>
                      <span className="badge-active shrink-0">{t('dashboard.active')}</span>
                    </div>
                    {contest.end_time && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-500 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {t('dashboard.endsOn', { date: formatDateTime(contest.end_time) })}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {featured && upcomingContests.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                {t('dashboard.upcomingContests')}
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {upcomingContests.map((contest) => (
                  <Link key={contest.id} to={`/contests/${contest.id}`} className="card-hover p-5 group">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="font-semibold text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                        {contest.title}
                      </h3>
                      <span className="badge bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300 shrink-0">
                        {t('dashboard.upcoming')}
                      </span>
                    </div>
                    {contest.start_time && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-500 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {t('dashboard.startsOn', { date: formatDateTime(contest.start_time) })}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {pastContests.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3">
                {t('dashboard.pastContests')}
              </h2>
              <div className="card divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {pastContests.map((contest) => (
                  <div key={contest.id} className="px-5 py-3.5 flex items-center gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-zinc-900 truncate dark:text-zinc-100">{contest.title}</p>
                      {contest.end_time && (
                        <p className="text-xs text-zinc-400 dark:text-zinc-500">
                          {formatDateTime(contest.end_time)}
                        </p>
                      )}
                    </div>
                    <Link
                      to={`/scoreboard/${contest.id}`}
                      className="text-sm font-medium text-accent-600 hover:text-accent-500 flex items-center gap-1 shrink-0 dark:text-accent-400 dark:hover:text-accent-300"
                    >
                      <Trophy className="w-3.5 h-3.5" /> {t('dashboard.results')}
                    </Link>
                    <Link
                      to={`/contests/${contest.id}`}
                      className="text-sm font-medium text-zinc-500 hover:text-zinc-800 flex items-center gap-1 shrink-0 dark:text-zinc-400 dark:hover:text-zinc-200"
                    >
                      {t('dashboard.view')} <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                    {user?.is_admin && (
                      <Link
                        to={`/scoreboard/${contest.id}/presentation`}
                        className="text-sm font-medium text-amber-600 hover:text-amber-500 flex items-center gap-1 shrink-0 dark:text-amber-300 dark:hover:text-amber-200"
                        title={t('presentation.entryTooltip')}
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* ── Side rail ───────────────────────────────────────────── */}
        <div className="space-y-6">
          <section className="card p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-4 flex items-center gap-2">
              <Users className="w-4 h-4" />
              {t('dashboard.myTeam')}
            </h2>
            {myTeam ? (
              <Link to="/teams" className="group flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-zinc-900 truncate group-hover:text-accent-600 dark:text-white dark:group-hover:text-accent-300">
                    {myTeam.name}
                  </p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {myTeam.members.length} {t('dashboard.members', { count: myTeam.members.length })}
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:text-accent-500 shrink-0" />
              </Link>
            ) : (
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">{t('dashboard.noTeamYet')}</p>
                <Link to="/teams" className="btn-primary text-sm inline-flex items-center">
                  {t('dashboard.joinOrCreate')}
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </Link>
              </div>
            )}
          </section>

          {rankings.length > 0 && (
            <section className="card p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-4 flex items-center gap-2">
                <Medal className="w-4 h-4" />
                {t('dashboard.yourRankings')}
              </h2>
              <div className="space-y-1">
                {rankings.map((r) => (
                  <Link
                    key={r.contest_id}
                    to={`/scoreboard/${r.contest_id}`}
                    className="group flex items-center gap-3 -mx-2 px-2 py-2 rounded-lg hover:bg-zinc-50 transition-colors dark:hover:bg-zinc-800/50"
                  >
                    <span
                      className={`w-9 h-9 rounded-full border flex items-center justify-center font-mono text-sm font-bold shrink-0 ${
                        MEDAL_RING[r.rank] || 'border-zinc-200 text-zinc-500 dark:border-zinc-700 dark:text-zinc-400'
                      }`}
                    >
                      {r.rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-900 truncate group-hover:text-accent-600 dark:text-zinc-100 dark:group-hover:text-accent-300">
                        {r.contest_title}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {t('dashboard.rankOf', { rank: r.rank, total: r.total_teams })}{' '}
                        <span className="font-mono tabular-nums font-semibold text-zinc-700 dark:text-zinc-300" title={formatScoreFull(r.total_score)}>
                          {formatScore(r.total_score)}
                        </span>
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          <section className="card p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
              <Medal className="w-4 h-4" />
              {t('nav.league')}
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">{t('dashboard.leagueTeaser')}</p>
            <Link to="/league" className="text-sm font-medium text-accent-600 hover:text-accent-500 inline-flex items-center gap-1 dark:text-accent-400 dark:hover:text-accent-300">
              {t('dashboard.leagueCta')} <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}
