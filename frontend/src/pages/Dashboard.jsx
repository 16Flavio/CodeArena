import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { getContests, getMyTeams, getMyRankings } from '../api';
import {
  Trophy, Users, Clock, ArrowRight, Flame, Target, Medal, Calendar, Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { formatScore, formatScoreFull } from '../utils/format';
import { formatDateTime, backendIsoMs } from '../utils/datetime';

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [contests, setContests] = useState([]);
  const [teams, setTeams] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getContests(), getMyTeams(), getMyRankings().catch(() => ({ data: [] }))])
      .then(([c, t, r]) => {
        setContests(c.data);
        setTeams(t.data);
        setRankings(r.data);
      })
      .catch(() => toast.error(t('dashboard.toastLoadFailed')))
      .finally(() => setLoading(false));
  }, []);

  const now = Date.now();
  // Mutually exclusive buckets: a contest in "past" never shows up in
  // "active" or "upcoming", even if practice mode keeps submissions open
  // after end_time. Order of precedence: past > active > upcoming.
  const isPast = (c) => {
    const end = backendIsoMs(c.end_time);
    return end != null && end <= now;
  };
  const pastContests = contests.filter(isPast);
  const activeContests = contests.filter((c) => !isPast(c) && c.is_open_for_submissions);
  const upcomingContests = contests.filter((c) => {
    if (isPast(c) || c.is_open_for_submissions) return false;
    const start = backendIsoMs(c.start_time);
    return start && start > now;
  });
  const myTeam = teams[0] || null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-zinc-900 mb-2 dark:text-white">
          {t('dashboard.welcome', { username: '' }).replace(',', '').trim()},{' '}
          <span className="text-accent-600 dark:text-accent-400">{user.username}</span>
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400">
          {t('dashboard.subtitle')}
        </p>
      </div>

      {/* Compact stats row: active, upcoming, total. No team count (at most one). */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          {
            label: t('dashboard.activeContests'),
            value: activeContests.length,
            icon: Flame,
            tile: 'bg-orange-100 text-orange-600 dark:bg-orange-950/50 dark:text-orange-400',
          },
          {
            label: t('dashboard.upcomingContests'),
            value: upcomingContests.length,
            icon: Calendar,
            tile: 'bg-sky-100 text-sky-600 dark:bg-sky-950/50 dark:text-sky-400',
          },
          {
            label: t('dashboard.totalContests'),
            value: contests.length,
            icon: Target,
            tile: 'bg-accent-100 text-accent-600 dark:bg-accent-950 dark:text-accent-400',
          },
        ].map((stat) => (
          <div key={stat.label} className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <div
                className={`w-10 h-10 rounded-md flex items-center justify-center ${stat.tile}`}
              >
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <p className="text-3xl font-bold text-zinc-900 font-mono dark:text-white">
              {stat.value}
            </p>
            <p className="text-sm text-zinc-500 mt-1 dark:text-zinc-400">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Compact single-team pill. Not a full grid — one team doesn't need one. */}
      <div>
        {myTeam ? (
          <Link
            to="/teams"
            className="card-hover p-4 flex items-center justify-between gap-3 group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-md bg-sky-100 text-sky-600 dark:bg-sky-950/50 dark:text-sky-400 flex items-center justify-center flex-shrink-0">
                <Users className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{t('dashboard.myTeam')}</p>
                <p className="font-semibold text-zinc-900 truncate group-hover:text-accent-600 dark:text-white dark:group-hover:text-accent-300">
                  {myTeam.name}
                  <span className="text-xs font-normal text-zinc-400 ml-2 dark:text-zinc-500">
                    {myTeam.members.length} {t('dashboard.members', { count: myTeam.members.length })}
                  </span>
                </p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-400 flex-shrink-0 group-hover:text-accent-500" />
          </Link>
        ) : (
          <div className="card p-4 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center flex-shrink-0 dark:bg-zinc-800">
                <Users className="w-5 h-5 text-zinc-400 dark:text-zinc-500" />
              </div>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">{t('dashboard.noTeamYet')}</p>
            </div>
            <Link to="/teams" className="btn-primary text-sm py-2 px-3">
              {t('dashboard.joinOrCreate')}
              <ArrowRight className="w-4 h-4 ml-1 inline" />
            </Link>
          </div>
        )}
      </div>

      {rankings.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-zinc-900 mb-4 flex items-center gap-2 dark:text-white">
            <Medal className="w-5 h-5 text-amber-500 dark:text-amber-400" />
            {t('dashboard.yourRankings')}
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {rankings.map((r) => {
              const medal = r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : null;
              return (
                <Link
                  key={r.contest_id}
                  to={`/scoreboard/${r.contest_id}`}
                  className="card-hover p-4 flex items-center gap-4"
                >
                  <div className="w-14 h-14 rounded-lg bg-accent-500/10 border border-accent-500/30 flex items-center justify-center flex-shrink-0">
                    {medal ? (
                      <span className="text-2xl" aria-hidden>{medal}</span>
                    ) : (
                      <span className="text-xl font-bold text-accent-700 dark:text-accent-300">#{r.rank}</span>
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-zinc-900 truncate dark:text-white">
                      {r.contest_title}
                    </p>
                    <p className="text-xs text-zinc-500 mt-0.5 dark:text-zinc-400">
                      {t('dashboard.rankOf', { rank: r.rank, total: r.total_teams })}{' '}
                      <span className="font-mono font-semibold text-zinc-700 dark:text-zinc-200" title={formatScoreFull(r.total_score)}>
                        {formatScore(r.total_score)}
                      </span>
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white">{t('dashboard.activeContests')}</h2>
        </div>

        {activeContests.length === 0 ? (
          <div className="card p-12 text-center">
            <Trophy className="w-12 h-12 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
            <p className="text-zinc-600 text-lg dark:text-zinc-400">{t('dashboard.noActiveContests')}</p>
            <p className="text-zinc-500 text-sm mt-2 dark:text-zinc-500">
              {t('dashboard.checkBackLater')}
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {activeContests.map((contest) => (
              <div key={contest.id} className="card-hover p-6 group">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                      {contest.title}
                    </h3>
                    <p className="text-zinc-500 text-sm mt-1 line-clamp-2 dark:text-zinc-400">
                      {contest.description || '—'}
                    </p>
                  </div>
                  <span className="badge-active">{t('dashboard.active')}</span>
                </div>

                <div className="flex items-center gap-4 text-sm text-zinc-500 mb-5 dark:text-zinc-500">
                  <span className="flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5" />
                    {contest.instance_count} {t('dashboard.instances', { count: contest.instance_count })}
                  </span>
                  {contest.end_time && (
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {t('dashboard.endsOn', { date: formatDateTime(contest.end_time) })}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    to={`/contests/${contest.id}`}
                    className="btn-primary text-sm py-2 px-4"
                  >
                    {t('dashboard.viewContest')}
                    <ArrowRight className="w-4 h-4 ml-1 inline" />
                  </Link>
                  <Link
                    to={`/scoreboard/${contest.id}`}
                    className="btn-secondary text-sm py-2 px-4"
                  >
                    <Trophy className="w-4 h-4 mr-1 inline" />
                    {t('dashboard.scoreboard')}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {upcomingContests.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-zinc-900 mb-4 flex items-center gap-2 dark:text-white">
            <Calendar className="w-5 h-5 text-sky-500 dark:text-sky-400" />
            {t('dashboard.upcomingContests')}
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingContests.map((contest) => (
              <div key={contest.id} className="card-hover p-5 group">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-base font-semibold text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                    {contest.title}
                  </h3>
                  <span className="badge bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300">
                    {t('dashboard.upcoming')}
                  </span>
                </div>
                <p className="text-zinc-500 text-sm mb-3 line-clamp-2 dark:text-zinc-500">
                  {contest.description || '—'}
                </p>
                {contest.start_time && (
                  <p className="text-xs text-zinc-500 mb-4 flex items-center gap-1.5 dark:text-zinc-500">
                    <Clock className="w-3.5 h-3.5" />
                    {t('dashboard.startsOn', { date: formatDateTime(contest.start_time) })}
                  </p>
                )}
                <Link
                  to={`/contests/${contest.id}`}
                  className="text-accent-600 hover:text-accent-500 text-sm font-medium flex items-center gap-1 dark:text-accent-400 dark:hover:text-accent-300"
                >
                  {t('dashboard.view')} <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {pastContests.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-zinc-900 mb-4 dark:text-white">{t('dashboard.pastContests')}</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pastContests.map((contest) => (
                <div key={contest.id} className="card-hover p-5 group">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-base font-semibold text-zinc-900 group-hover:text-accent-600 transition-colors dark:text-white dark:group-hover:text-accent-300">
                      {contest.title}
                    </h3>
                    <span className="badge-inactive">{t('dashboard.ended')}</span>
                  </div>
                  <p className="text-zinc-500 text-sm mb-4 line-clamp-2 dark:text-zinc-500">
                    {contest.description || '—'}
                  </p>
                  <div className="flex items-center gap-3 flex-wrap">
                    <Link
                      to={`/contests/${contest.id}`}
                      className="text-accent-600 hover:text-accent-500 text-sm font-medium flex items-center gap-1 dark:text-accent-400 dark:hover:text-accent-300"
                    >
                      {t('dashboard.view')} <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                    <Link
                      to={`/scoreboard/${contest.id}`}
                      className="text-zinc-500 hover:text-zinc-700 text-sm font-medium flex items-center gap-1 dark:text-zinc-400 dark:hover:text-zinc-300"
                    >
                      <Trophy className="w-3.5 h-3.5" /> {t('dashboard.results')}
                    </Link>
                    {user?.is_admin && (
                      <Link
                        to={`/scoreboard/${contest.id}/presentation`}
                        className="text-amber-600 hover:text-amber-500 text-sm font-medium flex items-center gap-1 dark:text-amber-300 dark:hover:text-amber-200"
                        title={t('presentation.entryTooltip')}
                      >
                        <Sparkles className="w-3.5 h-3.5" /> {t('dashboard.presentation')}
                      </Link>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
