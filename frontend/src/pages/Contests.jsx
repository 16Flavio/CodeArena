import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Trophy, Search, Calendar, Clock, ArrowRight, CheckCircle, Users, User, X,
} from 'lucide-react';
import { getContests, getMyRegisteredContestIds } from '../api';
import PageHeader from '../components/PageHeader';
import { formatDateTime, backendIsoMs } from '../utils/datetime';

// Buckets are mutually exclusive and use the same precedence as the
// dashboard (past > active > upcoming), so a contest never shows twice and
// the two pages never disagree about which state a contest is in.
const STATES = ['all', 'active', 'upcoming', 'past'];
const KINDS = ['all', 'icpc', 'output'];

function stateOf(contest, now) {
  const end = backendIsoMs(contest.end_time);
  if (end != null && end <= now) return 'past';
  if (contest.is_open_for_submissions) return 'active';
  return 'upcoming';
}

const STATE_BADGE = {
  active: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30 dark:text-emerald-400',
  upcoming: 'bg-accent-600/15 text-accent-700 border-accent-600/30 dark:text-accent-300',
  past: 'bg-zinc-500/15 text-zinc-600 border-zinc-400/30 dark:text-zinc-400',
};

export default function Contests() {
  const { t } = useTranslation();
  const [contests, setContests] = useState([]);
  const [registeredIds, setRegisteredIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [state, setState] = useState('all');
  const [kind, setKind] = useState('all');
  // Snapshotted once per mount rather than read during render: the buckets
  // only need to be right at load time, and Date.now() in render is impure.
  const [now] = useState(() => Date.now());

  useEffect(() => {
    Promise.all([
      getContests(),
      // Non-fatal: the badge is a nicety, the listing must render without it.
      getMyRegisteredContestIds().catch(() => ({ data: [] })),
    ])
      .then(([c, r]) => {
        setContests(c.data || []);
        setRegisteredIds(new Set(r.data || []));
      })
      .catch(() => toast.error(t('contests.loadFailed')))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const counts = useMemo(() => {
    const out = { all: contests.length, active: 0, upcoming: 0, past: 0 };
    contests.forEach((c) => { out[stateOf(c, now)] += 1; });
    return out;
  }, [contests, now]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return contests
      .filter((c) => (state === 'all' ? true : stateOf(c, now) === state))
      .filter((c) => (kind === 'all' ? true : (c.kind || 'output') === kind))
      .filter((c) => !q
        || c.title.toLowerCase().includes(q)
        || (c.description || '').toLowerCase().includes(q))
      .sort((a, b) => {
        // Running first, then soonest-starting, then most-recently-ended.
        const sa = stateOf(a, now);
        const sb = stateOf(b, now);
        const rank = { active: 0, upcoming: 1, past: 2 };
        if (rank[sa] !== rank[sb]) return rank[sa] - rank[sb];
        if (sa === 'past') {
          return (backendIsoMs(b.end_time) || 0) - (backendIsoMs(a.end_time) || 0);
        }
        return (backendIsoMs(a.start_time) || 0) - (backendIsoMs(b.start_time) || 0);
      });
  }, [contests, query, state, kind, now]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const chip = (active) =>
    `px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
      active
        ? 'bg-accent-600/15 text-accent-700 dark:bg-accent-600/20 dark:text-accent-300'
        : 'text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800/60'
    }`;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={t('contests.eyebrow')}
        title={t('contests.title')}
        description={t('contests.description')}
      />

      {/* Search + filters */}
      <div className="card p-4 mb-6 space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="search"
            className="input-field pl-9 pr-9 text-sm"
            placeholder={t('contests.searchPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={t('contests.searchPlaceholder')}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              aria-label={t('common.close')}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex flex-wrap items-center gap-1">
            {STATES.map((s) => (
              <button key={s} type="button" onClick={() => setState(s)} className={chip(state === s)}>
                {t(`contests.state.${s}`)}
                <span className="ml-1.5 text-[10px] tabular-nums opacity-60">{counts[s]}</span>
              </button>
            ))}
          </div>
          <span className="hidden sm:block w-px h-5 bg-zinc-200 dark:bg-zinc-800" />
          <div className="flex flex-wrap items-center gap-1">
            {KINDS.map((k) => (
              <button key={k} type="button" onClick={() => setKind(k)} className={chip(kind === k)}>
                {t(`contests.kind.${k}`)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="card p-10 text-center">
          <Trophy className="w-8 h-8 mx-auto text-zinc-300 mb-3 dark:text-zinc-700" />
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {contests.length === 0 ? t('contests.emptyAll') : t('contests.emptyFiltered')}
          </p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {visible.map((c) => {
            const s = stateOf(c, now);
            const isSolo = (c.participation_mode || 'team') === 'solo';
            return (
              <Link
                key={c.id}
                to={`/contests/${c.id}`}
                className="card p-4 flex flex-col gap-3 hover:border-accent-500/40 transition-colors group"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-semibold text-zinc-900 truncate dark:text-white">
                    {c.title}
                  </h2>
                  <span className={`shrink-0 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wide ${STATE_BADGE[s]}`}>
                    {t(`contests.state.${s}`)}
                  </span>
                </div>

                {c.description && (
                  <p className="text-xs text-zinc-500 line-clamp-2 dark:text-zinc-400">
                    {c.description}
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                  <span className="inline-flex items-center gap-1">
                    <Trophy className="w-3 h-3" />
                    {t(`contests.kind.${c.kind || 'output'}`)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    {isSolo ? <User className="w-3 h-3" /> : <Users className="w-3 h-3" />}
                    {t(`contests.mode.${c.participation_mode || 'team'}`)}
                  </span>
                  {c.start_time && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDateTime(c.start_time)}
                    </span>
                  )}
                  {c.end_time && (
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDateTime(c.end_time)}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between gap-2 pt-1 mt-auto border-t border-zinc-100 dark:border-zinc-800/60">
                  {registeredIds.has(c.id) ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                      <CheckCircle className="w-3.5 h-3.5" />
                      {t('contests.registered')}
                    </span>
                  ) : (
                    <span className="text-[11px] text-zinc-400 dark:text-zinc-600">
                      {t('contests.notRegistered')}
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent-600 dark:text-accent-400">
                    {t('contests.open')}
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
