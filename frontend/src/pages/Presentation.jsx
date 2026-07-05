import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Trophy, Play, Pause, ChevronRight, ChevronsRight, X, Award,
  Sparkles, Flame, Target, BarChart3, Zap, Clock, Code2, TrendingUp,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';
import { getIcpcPresentation, getScoringPresentation, getContest } from '../api';
import { textOn } from '../utils/contrast';
import { formatScore } from '../utils/format';
import { extractErrorMessage } from '../utils/apiError';

const ROW_HEIGHT = 56; // px - kept in sync with row CSS
const REVEAL_FLIP_MS = 280;

const SPEEDS = [
  { label: '×0.5', ms: 1600 },
  { label: '×1', ms: 800 },
  { label: '×2', ms: 400 },
  { label: '×4', ms: 200 },
];

const SCENES = ['intro', 'stats', 'reveal', 'podium'];

// Identity key for a row across solo/team scopes - IcpcScoreRow only carries
// team_id, so for solo entries we fall back to the username (team_name).
function rowKey(row) {
  return row.team_id != null ? `t:${row.team_id}` : `u:${row.team_name}`;
}

// Re-sort a list of rows in canonical ICPC order (most solved, then lowest
// penalty, then alphabetical) - same comparator as the backend.
function sortRows(rows) {
  return [...rows].sort((a, b) => {
    if (b.solved_count !== a.solved_count) return b.solved_count - a.solved_count;
    if (a.total_penalty !== b.total_penalty) return a.total_penalty - b.total_penalty;
    return a.team_name.localeCompare(b.team_name);
  });
}

// Recompute solved_count and total_penalty for a row from scratch given
// the current cells. Mirrors the backend's IcpcScoreRow aggregation.
function recomputeRowTotals(row) {
  let solved = 0;
  let penalty = 0;
  for (const label of Object.keys(row.cells)) {
    const c = row.cells[label];
    if (c && c.solved) {
      solved += 1;
      penalty += (c.first_solve_minutes || 0)
        + 20 * Math.max(0, (c.attempts || 1) - 1);
    }
  }
  return { ...row, solved_count: solved, total_penalty: penalty };
}

// Build the ordered list of reveal events from the frozen and final
// states. Implements the standard DOMjudge-style reveal:
//   1. Sort by current (working) frozen rank, descending (bottom up).
//   2. The bottom-most team with any frozen cell - pick its leftmost
//      such cell, reveal it (replace pending_attempts/attempts with
//      the truth), recompute totals, and re-sort.
//   3. Loop until no team has any frozen cell.
function buildRevealEvents(frozenRows, finalRows, problems) {
  const labels = problems.map((p) => p.label);
  const finalByKey = new Map(finalRows.map((r) => [rowKey(r), r]));

  // Working copy. Deep-clone cells so we don't mutate input.
  let state = frozenRows.map((r) => ({
    ...r,
    cells: Object.fromEntries(
      Object.entries(r.cells || {}).map(([k, v]) => [k, { ...v }])
    ),
  }));
  state = sortRows(state);

  const events = [];

  // Helper: does this cell still need to be revealed?
  // A cell needs reveal iff its working state differs from the final.
  const isFrozen = (cell, finalCell) => {
    if (!cell && !finalCell) return false;
    const a = cell || { solved: false, attempts: 0, first_solve_minutes: null, pending_attempts: 0 };
    const b = finalCell || { solved: false, attempts: 0, first_solve_minutes: null };
    if (a.solved !== b.solved) return true;
    if ((a.attempts || 0) !== (b.attempts || 0)) return true;
    if ((a.first_solve_minutes ?? null) !== (b.first_solve_minutes ?? null)) return true;
    if ((a.pending_attempts || 0) > 0) return true;
    return false;
  };

  // Loop guard - at most labels.length × rows.length events.
  const guard = labels.length * state.length + 1;
  let iter = 0;
  while (iter < guard) {
    iter += 1;
    state = sortRows(state);
    let target = null;
    let targetIdx = -1;
    let targetLabel = null;
    // Walk teams from bottom to top.
    for (let i = state.length - 1; i >= 0; i -= 1) {
      const row = state[i];
      const finalRow = finalByKey.get(rowKey(row));
      if (!finalRow) continue;
      // Find the leftmost label where this team has a frozen cell.
      const lab = labels.find((l) => isFrozen(row.cells[l], finalRow.cells[l]));
      if (lab) {
        target = row;
        targetIdx = i;
        targetLabel = lab;
        break;
      }
    }
    if (!target || !targetLabel) break;

    const finalRow = finalByKey.get(rowKey(target));
    const beforeCell = target.cells[targetLabel] || null;
    const afterCell = finalRow.cells[targetLabel] || null;
    const oldRank = targetIdx + 1;

    // Apply: replace cell, recompute totals.
    const updated = { ...target, cells: { ...target.cells, [targetLabel]: afterCell ? { ...afterCell, pending_attempts: 0 } : null } };
    const newTotals = recomputeRowTotals(updated);
    state = state.map((r) => (rowKey(r) === rowKey(target) ? newTotals : r));
    state = sortRows(state);
    const newIdx = state.findIndex((r) => rowKey(r) === rowKey(target));

    events.push({
      key: `${rowKey(target)}::${targetLabel}::${events.length}`,
      teamKey: rowKey(target),
      label: targetLabel,
      before: beforeCell,
      after: afterCell,
      oldRank,
      newRank: newIdx + 1,
      becameAc: !!(afterCell && afterCell.solved && !(beforeCell && beforeCell.solved)),
    });
  }

  return events;
}

export default function Presentation() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [kind, setKind] = useState(undefined);

  useEffect(() => {
    if (!user || !user.is_admin) return;
    getContest(id)
      .then((r) => setKind(r.data?.kind || 'output'))
      .catch(() => {
        toast.error(t('presentation.loadFailed'));
        navigate(`/scoreboard/${id}`);
      });
  }, [id, user, navigate, t]);

  if (!user || !user.is_admin) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500">
        {t('presentation.adminOnly')}
      </div>
    );
  }
  if (kind === undefined) {
    return (
      <div className="fixed inset-0 z-50 bg-zinc-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  return kind === 'icpc' ? <IcpcPresentationFlow /> : <ScoringPresentationFlow />;
}

function IcpcPresentationFlow() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [scene, setScene] = useState('intro');

  useEffect(() => {
    getIcpcPresentation(id)
      .then((r) => setData(r.data))
      .catch((err) => {
        toast.error(extractErrorMessage(err, t('presentation.loadFailed')));
        navigate(`/scoreboard/${id}`);
      });
  }, [id, navigate, t]);

  if (!data) {
    return (
      <div className="fixed inset-0 z-50 bg-zinc-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const goNext = () => {
    const i = SCENES.indexOf(scene);
    if (i < SCENES.length - 1) setScene(SCENES[i + 1]);
  };

  return (
    <div className="fixed inset-0 z-50 bg-zinc-950 text-white overflow-hidden">
      <button
        onClick={() => navigate(`/scoreboard/${id}`)}
        className="absolute top-4 right-4 z-20 p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
        title={t('presentation.exit')}
      >
        <X className="w-5 h-5" />
      </button>
      <SceneIndicator scene={scene} />

      {scene === 'intro' && <IntroScene title={data.contest_title} onStart={goNext} />}
      {scene === 'stats' && <StatsScene data={data} onContinue={goNext} />}
      {scene === 'reveal' && <RevealScene data={data} onComplete={goNext} />}
      {scene === 'podium' && <PodiumScene data={data} kind="icpc" />}
    </div>
  );
}

function SceneIndicator({ scene }) {
  const { t } = useTranslation();
  const i = SCENES.indexOf(scene);
  return (
    <div className="absolute top-4 left-4 z-20 flex gap-1.5">
      {SCENES.map((s, idx) => (
        <div
          key={s}
          className={`h-1.5 rounded-full transition-all duration-500 ${
            idx === i ? 'w-12 bg-accent-400' : idx < i ? 'w-6 bg-accent-700' : 'w-6 bg-white/15'
          }`}
          title={t(`presentation.scene.${s}`)}
        />
      ))}
    </div>
  );
}

function IntroScene({ title, onStart }) {
  const { t } = useTranslation();
  return (
    <div className="absolute inset-0 flex items-center justify-center flex-col gap-8 px-8 animate-fade-in">
      <div className="text-center space-y-4">
        <Sparkles className="w-16 h-16 mx-auto text-amber-300 animate-pulse" />
        <h1 className="text-6xl font-bold tracking-tight text-white">
          {title}
        </h1>
        <p className="text-xl text-white/70">{t('presentation.intro.tagline')}</p>
      </div>
      <button
        onClick={onStart}
        className="px-8 py-4 rounded-lg bg-accent-600 hover:bg-accent-500 text-lg font-semibold transition-all transform inline-flex items-center gap-3"
      >
        <Play className="w-6 h-6" />
        {t('presentation.intro.start')}
      </button>
    </div>
  );
}

function StatsScene({ data, onContinue }) {
  const { t } = useTranslation();
  // Aggregate from final state - already authoritative.
  const stats = useMemo(() => {
    const rows = data.final_state.rows;
    const totalTeams = rows.length;
    const teamsWithAc = rows.filter((r) => r.solved_count > 0).length;
    const totalSolves = rows.reduce((acc, r) => acc + r.solved_count, 0);
    let totalAttempts = 0;
    for (const r of rows) {
      for (const c of Object.values(r.cells || {})) {
        totalAttempts += c.attempts || 0;
      }
    }
    // First solver per problem - already in data.first_solvers.
    const firstSolvers = new Map(data.first_solvers.map((f) => [f.label, f]));
    // Hardest / easiest problems by solve count.
    const perProblem = data.problems.map((p) => {
      let solved = 0;
      let attempts = 0;
      for (const r of rows) {
        const c = r.cells?.[p.label];
        if (c?.solved) solved += 1;
        attempts += c?.attempts || 0;
      }
      return { ...p, solved, attempts, first: firstSolvers.get(p.label) || null };
    });
    return { totalTeams, teamsWithAc, totalSolves, totalAttempts, perProblem };
  }, [data]);

  return (
    <div className="absolute inset-0 px-8 py-16 overflow-y-auto animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-10">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 mx-auto text-accent-300" />
          <h2 className="text-4xl font-bold mt-2">{t('presentation.stats.heading')}</h2>
          <p className="text-white/60 mt-1">{data.contest_title}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <BigStat icon={<Target />} label={t('presentation.stats.teams')} value={stats.totalTeams} accent="violet" />
          <BigStat icon={<Zap />} label={t('presentation.stats.teamsWithAc')} value={stats.teamsWithAc} accent="emerald" />
          <BigStat icon={<Trophy />} label={t('presentation.stats.totalSolves')} value={stats.totalSolves} accent="amber" />
          <BigStat icon={<Flame />} label={t('presentation.stats.totalAttempts')} value={stats.totalAttempts} accent="rose" />
        </div>

        <LanguageChart languages={data.language_stats || []} />

        <div className="bg-white/5 border border-white/10 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-300" />
            {t('presentation.stats.firstSolvers')}
          </h3>
          {stats.perProblem.length === 0 && (
            <p className="text-white/50 italic">{t('presentation.stats.noProblems')}</p>
          )}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {stats.perProblem.map((p) => (
              <div key={p.id} className="flex items-center gap-3 bg-white/5 rounded-lg p-3 border border-white/10">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg"
                  style={{ background: p.color || '#a1a1aa', color: textOn(p.color || '#a1a1aa') }}
                >
                  {p.label}
                </div>
                <div className="min-w-0 flex-1">
                  {p.first ? (
                    <>
                      <div className="text-sm font-semibold truncate">{p.first.team_name}</div>
                      <div className="text-xs text-white/60 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {t('presentation.stats.atMinute', { n: p.first.minute })}
                        <span className="ml-2 text-white/40">- {p.solved}/{stats.totalTeams} {t('presentation.stats.solvedShort')}</span>
                      </div>
                    </>
                  ) : (
                    <div className="text-sm text-white/50 italic">{t('presentation.stats.unsolved')}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          <button
            onClick={onContinue}
            className="px-8 py-3 rounded-lg bg-accent-600 hover:bg-accent-500 text-base font-semibold inline-flex items-center gap-2"
          >
            {t('presentation.stats.continue')}
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Group raw language IDs into the three buckets the operator cares
// about (Python / C++ / others). The matchers are deliberately lenient
// so DOMjudge variants (py3 / py2 / pypy) and the various C++ wrappers
// (cpp / cpp17 / g++) all collapse to the same row.
const LANG_BUCKETS = [
  {
    key: 'python',
    label: 'Python',
    color: '#3776ab',
    accent: 'bg-sky-500/30 ring-sky-400/40',
    match: (id) => /^(py|python|pypy)/i.test(id),
  },
  {
    key: 'cpp',
    label: 'C++',
    color: '#9467bd',
    accent: 'bg-accent-500/30 ring-accent-400/40',
    match: (id) => /^(cpp|c\+\+|g\+\+|gcc-?cpp)/i.test(id),
  },
];

function LanguageChart({ languages }) {
  const { t } = useTranslation();
  const buckets = useMemo(() => {
    const out = LANG_BUCKETS.map((b) => ({ ...b, submissions: 0, accepted: 0, ids: [] }));
    const others = { key: 'other', label: t('presentation.stats.langOther'),
                     color: '#a1a1aa',
                     accent: 'bg-zinc-500/30 ring-zinc-400/40',
                     submissions: 0, accepted: 0, ids: [] };
    for (const l of languages) {
      const target = out.find((b) => b.match(l.language_id)) || others;
      target.submissions += l.submissions;
      target.accepted += l.accepted;
      target.ids.push(l.language_id);
    }
    const all = [...out, others].filter((b) => b.submissions > 0);
    all.sort((a, b) => b.submissions - a.submissions);
    return all;
  }, [languages, t]);

  const total = buckets.reduce((s, b) => s + b.submissions, 0);
  if (total === 0) return null;
  const maxSubs = buckets[0].submissions;

  return (
    <div className="bg-white/5 border border-white/10 rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Code2 className="w-5 h-5 text-accent-300" />
        {t('presentation.stats.langHeading')}
      </h3>
      <div className="space-y-3">
        {buckets.map((b) => {
          const widthPct = (b.submissions / maxSubs) * 100;
          const sharePct = total > 0 ? (b.submissions / total) * 100 : 0;
          const acRate = b.submissions > 0 ? (b.accepted / b.submissions) * 100 : 0;
          return (
            <div key={b.key} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{b.label}</span>
                  {b.key === 'other' && b.ids.length > 0 && (
                    <span className="text-xs text-white/50 truncate max-w-md">({b.ids.join(', ')})</span>
                  )}
                </div>
                <div className="text-xs text-white/60 font-mono tabular-nums">
                  {b.submissions} {t('presentation.stats.langSubs')} · {b.accepted} AC ({acRate.toFixed(0)}%) · {sharePct.toFixed(0)}%
                </div>
              </div>
              <div className="h-6 bg-white/5 rounded-md overflow-hidden ring-1 ring-white/10 relative">
                <div
                  className={`h-full ${b.accent} ring-1 transition-[width] duration-700 ease-out flex items-center px-2`}
                  style={{ width: `${widthPct}%` }}
                >
                  {/* AC slice - overlay a darker portion to show the AC fraction. */}
                  <div
                    className="absolute left-0 top-0 h-full bg-white/15"
                    style={{ width: `${(b.accepted / maxSubs) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-white/40 mt-4">
        {t('presentation.stats.langLegend')}
      </p>
    </div>
  );
}

function BigStat({ icon, label, value, accent }) {
  const accents = {
    violet: 'bg-accent-500/15 text-accent-200 border-accent-400/30',
    emerald: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/30',
    amber: 'bg-amber-500/15 text-amber-200 border-amber-400/30',
    rose: 'bg-rose-500/15 text-rose-200 border-rose-400/30',
  };
  return (
    <div className={`${accents[accent]} border rounded-lg p-5`}>
      <div className="flex items-center justify-between mb-2 opacity-80">
        <span className="text-xs uppercase tracking-wider">{label}</span>
        <span className="w-5 h-5">{icon}</span>
      </div>
      <div className="text-4xl font-bold tabular-nums">{value}</div>
    </div>
  );
}

function RevealScene({ data, onComplete }) {
  const { t } = useTranslation();
  const events = useMemo(
    () => buildRevealEvents(data.frozen_state.rows, data.final_state.rows, data.problems),
    [data]
  );

  // Working state - start from frozen.
  const [rows, setRows] = useState(() =>
    sortRows(data.frozen_state.rows.map((r) => ({
      ...r,
      cells: Object.fromEntries(
        Object.entries(r.cells || {}).map(([k, v]) => [k, { ...v }])
      ),
    })))
  );
  const [eventIdx, setEventIdx] = useState(-1); // -1 = before any event
  const [playing, setPlaying] = useState(true);
  const [speedIdx, setSpeedIdx] = useState(1); // ×1 default
  const [flipKey, setFlipKey] = useState(null); // {teamKey, label} of cell currently flipping
  const [announcement, setAnnouncement] = useState(null);
  const firstSolvers = useMemo(
    () => new Map(data.first_solvers.map((f) => [f.label, f])),
    [data.first_solvers]
  );
  const announcementTimer = useRef(null);

  // Apply event N - mutate rows + maybe trigger announcement.
  const applyEvent = (n) => {
    if (n < 0 || n >= events.length) return;
    const ev = events[n];
    // Flash the flip on the cell before applying the change (for the
    // CSS scaleY 1→0→1 effect). The change itself happens at mid-flip.
    setFlipKey({ teamKey: ev.teamKey, label: ev.label });
    setTimeout(() => {
      setRows((prev) => {
        const next = prev.map((r) => {
          if (rowKey(r) !== ev.teamKey) return r;
          const nextCell = ev.after ? { ...ev.after, pending_attempts: 0 } : null;
          const updated = { ...r, cells: { ...r.cells, [ev.label]: nextCell } };
          return recomputeRowTotals(updated);
        });
        return sortRows(next);
      });
      setFlipKey(null);
      // First-to-solve announcement.
      if (ev.becameAc) {
        const fs = firstSolvers.get(ev.label);
        const teamRow = data.final_state.rows.find((r) => rowKey(r) === ev.teamKey);
        if (fs && teamRow && fs.team_name === teamRow.team_name) {
          // This team is the official first solver of this problem.
          if (announcementTimer.current) clearTimeout(announcementTimer.current);
          setAnnouncement({ label: ev.label, team_name: teamRow.team_name, members: teamRow.members, minute: fs.minute });
          announcementTimer.current = setTimeout(() => setAnnouncement(null), 2500);
        }
      }
    }, REVEAL_FLIP_MS / 2);
  };

  // Auto-play loop.
  useEffect(() => {
    if (!playing) return undefined;
    if (eventIdx >= events.length - 1) {
      // Reveal finished - give a beat, then advance to podium.
      const id = setTimeout(() => onComplete(), 1500);
      return () => clearTimeout(id);
    }
    const ms = SPEEDS[speedIdx].ms;
    const timer = setTimeout(() => {
      setEventIdx((i) => {
        const next = i + 1;
        applyEvent(next);
        return next;
      });
    }, ms);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, eventIdx, speedIdx, events.length]);

  const stepForward = () => {
    setPlaying(false);
    if (eventIdx >= events.length - 1) return;
    setEventIdx((i) => {
      const next = i + 1;
      applyEvent(next);
      return next;
    });
  };

  return (
    <div className="absolute inset-0 flex flex-col">
      <div className="px-6 pt-16 pb-3 text-center">
        <h2 className="text-2xl font-bold text-amber-300 flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6" />
          {t('presentation.reveal.heading')}
        </h2>
        <p className="text-white/50 text-sm mt-1">
          {t('presentation.reveal.progress', { n: Math.max(0, eventIdx + 1), total: events.length })}
        </p>
      </div>
      <RevealBoard
        rows={rows}
        problems={data.problems}
        flipKey={flipKey}
        eventIdx={eventIdx}
        events={events}
      />
      <RevealControls
        playing={playing}
        onPlayPause={() => setPlaying((p) => !p)}
        onStep={stepForward}
        onSkip={() => {
          // Apply all remaining events synchronously.
          for (let i = eventIdx + 1; i < events.length; i += 1) {
            const ev = events[i];
            setRows((prev) => {
              const next = prev.map((r) => {
                if (rowKey(r) !== ev.teamKey) return r;
                const nextCell = ev.after ? { ...ev.after, pending_attempts: 0 } : null;
                const updated = { ...r, cells: { ...r.cells, [ev.label]: nextCell } };
                return recomputeRowTotals(updated);
              });
              return sortRows(next);
            });
          }
          setEventIdx(events.length - 1);
        }}
        speedIdx={speedIdx}
        onSpeed={setSpeedIdx}
      />
      {announcement && <FirstSolveOverlay announcement={announcement} problems={data.problems} />}
    </div>
  );
}

function RevealBoard({ rows, problems, flipKey }) {
  const { t } = useTranslation();
  // Maintain stable team ordering for absolute positioning so React keeps
  // the DOM nodes across re-sorts and CSS animates the transform.
  const orderedKeys = useMemo(
    () => rows.map((r) => rowKey(r)),
    [rows]
  );
  const rankByKey = useMemo(() => {
    const m = new Map();
    orderedKeys.forEach((k, i) => m.set(k, i));
    return m;
  }, [orderedKeys]);

  return (
    <div className="flex-1 px-6 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div className="sticky top-0 z-10 grid items-center bg-zinc-900/80 border-b border-white/10 py-2 text-xs uppercase tracking-wider text-white/60"
             style={{ gridTemplateColumns: `48px minmax(180px, 1fr) 70px 90px repeat(${problems.length}, 56px)` }}>
          <div className="text-center">#</div>
          <div className="px-3">{t('presentation.reveal.team')}</div>
          <div className="text-right pr-2">{t('presentation.reveal.solved')}</div>
          <div className="text-right pr-2">{t('presentation.reveal.penalty')}</div>
          {problems.map((p) => (
            <div key={p.id} className="flex justify-center">
              <span
                className="w-7 h-7 rounded-full text-xs font-bold leading-7 text-center"
                style={{ background: p.color || '#a1a1aa', color: textOn(p.color || '#a1a1aa') }}
              >
                {p.label}
              </span>
            </div>
          ))}
        </div>
        <div className="relative" style={{ height: rows.length * ROW_HEIGHT + 4 }}>
          {rows.map((r) => {
            const key = rowKey(r);
            const rank = rankByKey.get(key) ?? 0;
            const medal = rank === 0 ? 'gold' : rank === 1 ? 'silver' : rank === 2 ? 'bronze' : null;
            return (
              <div
                key={key}
                className={`absolute left-0 right-0 grid items-center rounded-lg my-0.5 transition-[transform,background-color] duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${
                  medal === 'gold' ? 'bg-amber-400/15 ring-1 ring-amber-300/40'
                  : medal === 'silver' ? 'bg-zinc-300/10 ring-1 ring-zinc-300/30'
                  : medal === 'bronze' ? 'bg-amber-700/10 ring-1 ring-amber-600/30'
                  : 'bg-white/5'
                }`}
                style={{
                  transform: `translateY(${rank * ROW_HEIGHT}px)`,
                  height: ROW_HEIGHT - 4,
                  gridTemplateColumns: `48px minmax(180px, 1fr) 70px 90px repeat(${problems.length}, 56px)`,
                }}
              >
                <div className="text-center font-mono text-lg font-bold tabular-nums">
                  {medal === 'gold' ? '🥇' : medal === 'silver' ? '🥈' : medal === 'bronze' ? '🥉' : rank + 1}
                </div>
                <div className="px-3 min-w-0">
                  <div className="font-semibold truncate">{r.team_name}</div>
                  {r.affiliation_name && (
                    <div className="text-xs text-white/50 truncate">{r.affiliation_name}</div>
                  )}
                </div>
                <div className="text-right pr-2 font-mono text-lg font-bold tabular-nums text-accent-300">
                  {r.solved_count}
                </div>
                <div className="text-right pr-2 font-mono text-sm tabular-nums text-white/70">
                  {r.total_penalty}
                </div>
                {problems.map((p) => {
                  const cell = r.cells?.[p.label];
                  const isFlipping = flipKey && flipKey.teamKey === key && flipKey.label === p.label;
                  return (
                    <div key={p.id} className="flex justify-center">
                      <RevealCell cell={cell} flipping={isFlipping} />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function RevealCell({ cell, flipping }) {
  if (!cell) {
    return (
      <span className="w-10 h-9 rounded text-xs flex items-center justify-center text-white/20">-</span>
    );
  }
  const isPending = (cell.pending_attempts || 0) > 0 && !cell.solved;
  const display = cell.solved
    ? { text: `+${cell.attempts || 1}`, sub: `${cell.first_solve_minutes ?? 0}'`, cls: 'bg-emerald-500/25 text-emerald-100 ring-1 ring-emerald-400/40' }
    : isPending
      ? { text: '?', sub: '', cls: 'bg-sky-500/25 text-sky-100 ring-1 ring-sky-400/40' }
      : (cell.attempts || 0) > 0
        ? { text: `−${cell.attempts}`, sub: '', cls: 'bg-red-500/25 text-red-100 ring-1 ring-red-400/40' }
        : { text: '', sub: '', cls: '' };
  return (
    <span
      className={`w-10 h-9 rounded text-xs font-mono flex flex-col items-center justify-center transition-transform duration-150 ${
        display.cls
      } ${flipping ? 'scale-y-0' : 'scale-y-100'}`}
      style={flipping ? { transitionDuration: `${REVEAL_FLIP_MS / 2}ms` } : undefined}
    >
      <span className="font-bold leading-none">{display.text}</span>
      {display.sub && <span className="text-[9px] opacity-70 leading-none mt-0.5">{display.sub}</span>}
    </span>
  );
}

function RevealControls({ playing, onPlayPause, onStep, onSkip, speedIdx, onSpeed }) {
  const { t } = useTranslation();
  return (
    <div className="px-6 py-3 bg-zinc-900/80 border-t border-white/10 flex items-center justify-center gap-3">
      <button
        onClick={onPlayPause}
        className="px-4 py-2 rounded-lg bg-accent-500 hover:bg-accent-400 transition-colors font-medium inline-flex items-center gap-2"
        title={playing ? t('presentation.reveal.pause') : t('presentation.reveal.play')}
      >
        {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        {playing ? t('presentation.reveal.pause') : t('presentation.reveal.play')}
      </button>
      <button
        onClick={onStep}
        className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors inline-flex items-center gap-2 text-sm"
        title={t('presentation.reveal.step')}
      >
        <ChevronRight className="w-4 h-4" />
        {t('presentation.reveal.step')}
      </button>
      <button
        onClick={onSkip}
        className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors inline-flex items-center gap-2 text-sm"
        title={t('presentation.reveal.skip')}
      >
        <ChevronsRight className="w-4 h-4" />
        {t('presentation.reveal.skip')}
      </button>
      <div className="ml-4 flex items-center gap-1 bg-white/5 rounded-lg p-1">
        {SPEEDS.map((s, i) => (
          <button
            key={s.label}
            onClick={() => onSpeed(i)}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
              i === speedIdx ? 'bg-accent-500 text-white' : 'text-white/70 hover:bg-white/10'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function FirstSolveOverlay({ announcement, problems }) {
  const { t } = useTranslation();
  const p = problems.find((x) => x.label === announcement.label);
  const color = p?.color || '#f59e0b';
  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none animate-fade-in">
      <div className="bg-zinc-900/90 border border-amber-300/40 rounded-lg px-12 py-8 shadow-2xl shadow-amber-500/30 max-w-2xl text-center">
        <div className="text-amber-300 text-sm uppercase tracking-widest font-bold mb-2 flex items-center justify-center gap-2">
          🎈 {t('presentation.firstSolve.heading')}
        </div>
        <div
          className="inline-block w-20 h-20 rounded-lg text-4xl font-bold leading-[80px] mb-3"
          style={{ background: color, color: textOn(color) }}
        >
          {announcement.label}
        </div>
        <div className="text-3xl font-bold mt-2">{announcement.team_name}</div>
        {announcement.members?.length > 0 && (
          <div className="text-white/60 text-sm mt-1">{announcement.members.join(' · ')}</div>
        )}
        <div className="text-amber-300 text-lg font-mono mt-3 tabular-nums">
          {t('presentation.firstSolve.atMinute', { n: announcement.minute })}
        </div>
      </div>
    </div>
  );
}

function PodiumScene({ data, kind }) {
  const { t } = useTranslation();
  // Group medals by tier; reveal one row at a time, bronze → silver → gold,
  // bottom-rank within each group first so the camera "rises".
  const groups = useMemo(() => {
    const g = { bronze: [], silver: [], gold: [] };
    for (const m of data.medals) {
      if (m.tier && g[m.tier]) g[m.tier].push(m);
    }
    g.bronze.sort((a, b) => b.rank - a.rank);
    g.silver.sort((a, b) => b.rank - a.rank);
    g.gold.sort((a, b) => b.rank - a.rank);
    return g;
  }, [data.medals]);

  const order = useMemo(() => [...groups.bronze, ...groups.silver, ...groups.gold], [groups]);
  const [revealedCount, setRevealedCount] = useState(0);

  useEffect(() => {
    if (revealedCount >= order.length) return undefined;
    const timer = setTimeout(() => setRevealedCount((c) => c + 1), revealedCount === 0 ? 800 : 1300);
    return () => clearTimeout(timer);
  }, [revealedCount, order.length]);

  return (
    <div className="absolute inset-0 px-8 py-16 overflow-y-auto animate-fade-in">
      <div className="max-w-5xl mx-auto space-y-12">
        <div className="text-center">
          <Trophy className="w-16 h-16 mx-auto text-amber-300" />
          <h2 className="text-5xl font-bold mt-3 text-amber-300">
            {t('presentation.podium.heading')}
          </h2>
          <p className="text-white/60 mt-2">{data.contest_title}</p>
        </div>

        <PodiumGroup tier="gold"   group={groups.gold}   order={order} revealedCount={revealedCount} kind={kind} />
        <PodiumGroup tier="silver" group={groups.silver} order={order} revealedCount={revealedCount} kind={kind} />
        <PodiumGroup tier="bronze" group={groups.bronze} order={order} revealedCount={revealedCount} kind={kind} />
      </div>
    </div>
  );
}

function PodiumGroup({ tier, group, order, revealedCount, kind }) {
  const { t } = useTranslation();
  const tierStyle = {
    gold: { bg: 'bg-gradient-to-br from-amber-400/20 to-amber-700/10 border-amber-400/40', icon: '🥇', label: t('presentation.podium.goldHeading') },
    silver: { bg: 'bg-gradient-to-br from-zinc-300/20 to-zinc-500/10 border-zinc-300/40', icon: '🥈', label: t('presentation.podium.silverHeading') },
    bronze: { bg: 'bg-gradient-to-br from-amber-700/20 to-amber-900/10 border-amber-700/40', icon: '🥉', label: t('presentation.podium.bronzeHeading') },
  }[tier];

  if (group.length === 0) return null;
  const display = [...group].sort((a, b) => a.rank - b.rank);

  // ICPC: two side metrics (solved + penalty). Scoring: one (total_score).
  const isIcpc = kind === 'icpc';
  const gridCols = isIcpc ? '60px 1fr 90px 110px' : '60px 1fr 160px';

  return (
    <div className={`${tierStyle.bg} border rounded-lg p-6`}>
      <h3 className="text-2xl font-bold flex items-center gap-3 mb-4">
        <span className="text-3xl">{tierStyle.icon}</span>
        {tierStyle.label}
        <span className="text-sm font-normal text-white/50">{t('presentation.podium.ranksRange', { from: display[0].rank, to: display[display.length - 1].rank })}</span>
      </h3>
      <div className="space-y-2">
        {display.map((m) => {
          const idx = order.findIndex((o) => o.rank === m.rank);
          const revealed = idx < revealedCount;
          return (
            <div
              key={m.rank}
              className={`grid items-center bg-white/5 rounded-lg px-5 py-3 border border-white/10 transition-all duration-700 ease-out ${
                revealed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
              }`}
              style={{ gridTemplateColumns: gridCols }}
            >
              <div className="text-3xl font-bold tabular-nums">{m.rank}</div>
              <div className="min-w-0">
                <div className="text-xl font-semibold truncate">{m.team_name}</div>
                {m.members?.length > 0 && (
                  <div className="text-xs text-white/55 truncate">{m.members.join(' · ')}</div>
                )}
                {m.affiliation_name && (
                  <div className="text-xs text-white/40 truncate">{m.affiliation_name}</div>
                )}
              </div>
              {isIcpc ? (
                <>
                  <div className="text-right">
                    <div className="text-2xl font-bold tabular-nums text-accent-200">{m.solved_count}</div>
                    <div className="text-[10px] uppercase tracking-wider text-white/50">{t('presentation.podium.solved')}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-mono tabular-nums text-white/70">{m.total_penalty}</div>
                    <div className="text-[10px] uppercase tracking-wider text-white/50">{t('presentation.podium.penalty')}</div>
                  </div>
                </>
              ) : (
                <div className="text-right">
                  <div className="text-2xl font-bold tabular-nums text-accent-200">{formatScore(m.total_score)}</div>
                  <div className="text-[10px] uppercase tracking-wider text-white/50">{t('presentation.podium.totalScore')}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ─── Scoring (Hashcode-style) presentation flow ──────────────────────────────

function teamScoreKey(t) {
  return t.team_id != null ? `t:${t.team_id}` : `u:${t.team_name}`;
}

function sortTeamsByScore(teams) {
  return [...teams].sort((a, b) => {
    if (b.total_score !== a.total_score) return b.total_score - a.total_score;
    return a.team_name.localeCompare(b.team_name);
  });
}

function recomputeTotal(team) {
  let total = 0;
  for (const cell of Object.values(team.scores || {})) {
    total += cell?.best_score || 0;
  }
  return { ...team, total_score: total };
}

// DOMjudge-style reveal adapted to numeric scores. A cell is "frozen"
// iff ``pending_changes > 0`` in the current working state. We pick the
// bottom-most team's leftmost frozen cell, replace it with the truth,
// recompute the team total, and re-sort.
function buildScoringRevealEvents(frozenState, finalState) {
  const instances = frozenState.instances;
  const finalByKey = new Map(finalState.teams.map((t) => [teamScoreKey(t), t]));

  let state = sortTeamsByScore(frozenState.teams.map((t) => ({
    ...t,
    scores: Object.fromEntries(
      Object.entries(t.scores || {}).map(([k, v]) => [k, { ...v }])
    ),
  })));

  const events = [];
  const guard = instances.length * state.length + 1;
  let iter = 0;
  while (iter < guard) {
    iter += 1;
    state = sortTeamsByScore(state);
    let target = null;
    let targetKey = null;
    let targetInstId = null;
    for (let i = state.length - 1; i >= 0; i -= 1) {
      const row = state[i];
      const inst = instances.find((x) => (row.scores[String(x.id)]?.pending_changes || 0) > 0);
      if (inst) {
        target = row;
        targetKey = teamScoreKey(row);
        targetInstId = inst.id;
        break;
      }
    }
    if (!target || targetInstId == null) break;

    const finalRow = finalByKey.get(targetKey);
    const beforeCell = target.scores[String(targetInstId)] || null;
    const afterCell = finalRow?.scores[String(targetInstId)] || beforeCell;
    const sanitised = { ...afterCell, pending_changes: 0 };
    const updated = { ...target, scores: { ...target.scores, [String(targetInstId)]: sanitised } };
    const withTotal = recomputeTotal(updated);

    state = state.map((r) => (teamScoreKey(r) === targetKey ? withTotal : r));
    state = sortTeamsByScore(state);

    events.push({
      key: `${targetKey}::${targetInstId}::${events.length}`,
      teamKey: targetKey,
      instanceId: targetInstId,
      before: beforeCell,
      after: sanitised,
      delta: (afterCell?.best_score || 0) - (beforeCell?.best_score || 0),
    });
  }
  return events;
}

function ScoringPresentationFlow() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [scene, setScene] = useState('intro');

  useEffect(() => {
    getScoringPresentation(id)
      .then((r) => setData(r.data))
      .catch((err) => {
        toast.error(extractErrorMessage(err, t('presentation.loadFailed')));
        navigate(`/scoreboard/${id}`);
      });
  }, [id, navigate, t]);

  if (!data) {
    return (
      <div className="fixed inset-0 z-50 bg-zinc-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const goNext = () => {
    const i = SCENES.indexOf(scene);
    if (i < SCENES.length - 1) setScene(SCENES[i + 1]);
  };

  return (
    <div className="fixed inset-0 z-50 bg-zinc-950 text-white overflow-hidden">
      <button
        onClick={() => navigate(`/scoreboard/${id}`)}
        className="absolute top-4 right-4 z-20 p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
        title={t('presentation.exit')}
      >
        <X className="w-5 h-5" />
      </button>
      <SceneIndicator scene={scene} />

      {scene === 'intro' && <IntroScene title={data.contest_title} onStart={goNext} />}
      {scene === 'stats' && <ScoringStatsScene data={data} onContinue={goNext} />}
      {scene === 'reveal' && <ScoringRevealScene data={data} onComplete={goNext} />}
      {scene === 'podium' && <PodiumScene data={data} kind="output" />}
    </div>
  );
}

function ScoringStatsScene({ data, onContinue }) {
  const { t } = useTranslation();
  const stats = useMemo(() => {
    const teams = data.final_state.teams;
    const totalTeams = teams.length;
    const teamsScoring = teams.filter((tm) => tm.total_score > 0).length;
    let totalSubs = 0;
    for (const tm of teams) {
      for (const c of Object.values(tm.scores || {})) {
        totalSubs += c.submission_count || 0;
      }
    }
    const topScore = teams.reduce((acc, tm) => Math.max(acc, tm.total_score || 0), 0);
    const bestByInstance = new Map(data.instance_bests.map((b) => [b.instance_id, b]));
    const perInstance = data.instances.map((inst) => {
      let scorers = 0;
      for (const tm of teams) {
        const c = tm.scores?.[String(inst.id)];
        if (c && c.best_score > 0) scorers += 1;
      }
      return { ...inst, best: bestByInstance.get(inst.id) || null, scorers };
    });
    return { totalTeams, teamsScoring, totalSubs, topScore, perInstance };
  }, [data]);

  return (
    <div className="absolute inset-0 px-8 py-16 overflow-y-auto animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-10">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 mx-auto text-accent-300" />
          <h2 className="text-4xl font-bold mt-2">{t('presentation.stats.heading')}</h2>
          <p className="text-white/60 mt-1">{data.contest_title}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <BigStat icon={<Target />} label={t('presentation.stats.teams')} value={stats.totalTeams} accent="violet" />
          <BigStat icon={<Zap />} label={t('presentation.stats.scoringTeams')} value={stats.teamsScoring} accent="emerald" />
          <BigStat icon={<TrendingUp />} label={t('presentation.stats.topScore')} value={formatScore(stats.topScore)} accent="amber" />
          <BigStat icon={<Flame />} label={t('presentation.stats.totalSubmissions')} value={stats.totalSubs} accent="rose" />
        </div>

        <div className="bg-white/5 border border-white/10 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-300" />
            {t('presentation.stats.bestPerInstance')}
          </h3>
          {stats.perInstance.length === 0 && (
            <p className="text-white/50 italic">{t('presentation.stats.noInstances')}</p>
          )}
          <div className="grid sm:grid-cols-2 lg:grid-cols-2 gap-3">
            {stats.perInstance.map((inst) => (
              <div key={inst.id} className="flex items-center gap-3 bg-white/5 rounded-lg p-3 border border-white/10">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-accent-500/30 text-accent-100 font-bold text-base flex-shrink-0">
                  {inst.name.slice(0, 3).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-white/60 truncate">{inst.name}</div>
                  {inst.best ? (
                    <>
                      <div className="text-base font-semibold truncate">{inst.best.team_name}</div>
                      <div className="text-xs text-amber-300 font-mono tabular-nums">
                        {formatScore(inst.best.best_score)}
                        <span className="ml-2 text-white/40">- {inst.scorers}/{stats.totalTeams} {t('presentation.stats.scorersShort')}</span>
                      </div>
                    </>
                  ) : (
                    <div className="text-sm text-white/50 italic">{t('presentation.stats.noScores')}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          <button
            onClick={onContinue}
            className="px-8 py-3 rounded-lg bg-accent-600 hover:bg-accent-500 text-base font-semibold inline-flex items-center gap-2"
          >
            {t('presentation.stats.continue')}
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ScoringRevealScene({ data, onComplete }) {
  const { t } = useTranslation();
  const events = useMemo(
    () => buildScoringRevealEvents(data.frozen_state, data.final_state),
    [data]
  );

  const [teams, setTeams] = useState(() =>
    sortTeamsByScore(data.frozen_state.teams.map((tm) => ({
      ...tm,
      scores: Object.fromEntries(
        Object.entries(tm.scores || {}).map(([k, v]) => [k, { ...v }])
      ),
    })))
  );
  const [eventIdx, setEventIdx] = useState(-1);
  const [playing, setPlaying] = useState(true);
  const [speedIdx, setSpeedIdx] = useState(1);
  const [flipKey, setFlipKey] = useState(null);
  const [announcement, setAnnouncement] = useState(null);
  const announcementTimer = useRef(null);
  const bestByInstance = useMemo(
    () => new Map(data.instance_bests.map((b) => [b.instance_id, b])),
    [data.instance_bests]
  );

  const applyEvent = (n) => {
    if (n < 0 || n >= events.length) return;
    const ev = events[n];
    setFlipKey({ teamKey: ev.teamKey, instanceId: ev.instanceId });
    setTimeout(() => {
      setTeams((prev) => {
        const next = prev.map((tm) => {
          if (teamScoreKey(tm) !== ev.teamKey) return tm;
          const updated = { ...tm, scores: { ...tm.scores, [String(ev.instanceId)]: ev.after } };
          return recomputeTotal(updated);
        });
        return sortTeamsByScore(next);
      });
      setFlipKey(null);
      // Best-on-instance announcement: this revealed cell matches the
      // pre-computed global best for the instance, AND the score
      // actually changed (so the reveal "earned" the title).
      const best = bestByInstance.get(ev.instanceId);
      const teamRow = data.final_state.teams.find((tm) => teamScoreKey(tm) === ev.teamKey);
      if (best && teamRow && best.team_name === teamRow.team_name && ev.delta !== 0) {
        if (announcementTimer.current) clearTimeout(announcementTimer.current);
        const inst = data.instances.find((i) => i.id === ev.instanceId);
        setAnnouncement({ instanceName: inst?.name || '', team_name: teamRow.team_name, members: teamRow.members, score: best.best_score });
        announcementTimer.current = setTimeout(() => setAnnouncement(null), 2500);
      }
    }, REVEAL_FLIP_MS / 2);
  };

  useEffect(() => {
    if (!playing) return undefined;
    if (eventIdx >= events.length - 1) {
      const id = setTimeout(() => onComplete(), 1500);
      return () => clearTimeout(id);
    }
    const ms = SPEEDS[speedIdx].ms;
    const timer = setTimeout(() => {
      setEventIdx((i) => {
        const next = i + 1;
        applyEvent(next);
        return next;
      });
    }, ms);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, eventIdx, speedIdx, events.length]);

  const stepForward = () => {
    setPlaying(false);
    if (eventIdx >= events.length - 1) return;
    setEventIdx((i) => {
      const next = i + 1;
      applyEvent(next);
      return next;
    });
  };

  const skipAll = () => {
    setPlaying(false);
    for (let i = eventIdx + 1; i < events.length; i += 1) {
      const ev = events[i];
      setTeams((prev) => {
        const next = prev.map((tm) => {
          if (teamScoreKey(tm) !== ev.teamKey) return tm;
          const updated = { ...tm, scores: { ...tm.scores, [String(ev.instanceId)]: ev.after } };
          return recomputeTotal(updated);
        });
        return sortTeamsByScore(next);
      });
    }
    setEventIdx(events.length - 1);
  };

  return (
    <div className="absolute inset-0 flex flex-col">
      <div className="px-6 pt-16 pb-3 text-center">
        <h2 className="text-2xl font-bold text-amber-300 flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6" />
          {t('presentation.reveal.heading')}
        </h2>
        <p className="text-white/50 text-sm mt-1">
          {t('presentation.reveal.progress', { n: Math.max(0, eventIdx + 1), total: events.length })}
        </p>
      </div>
      <ScoringRevealBoard
        teams={teams}
        instances={data.instances}
        flipKey={flipKey}
      />
      <RevealControls
        playing={playing}
        onPlayPause={() => setPlaying((p) => !p)}
        onStep={stepForward}
        onSkip={skipAll}
        speedIdx={speedIdx}
        onSpeed={setSpeedIdx}
      />
      {announcement && <BestScoreOverlay announcement={announcement} />}
    </div>
  );
}

function ScoringRevealBoard({ teams, instances, flipKey }) {
  const { t } = useTranslation();
  const orderedKeys = useMemo(() => teams.map(teamScoreKey), [teams]);
  const rankByKey = useMemo(() => {
    const m = new Map();
    orderedKeys.forEach((k, i) => m.set(k, i));
    return m;
  }, [orderedKeys]);

  return (
    <div className="flex-1 px-6 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div
          className="sticky top-0 z-10 grid items-center bg-zinc-900/80 border-b border-white/10 py-2 text-xs uppercase tracking-wider text-white/60"
          style={{ gridTemplateColumns: `48px minmax(180px, 1fr) 110px repeat(${instances.length}, minmax(72px, 1fr))` }}
        >
          <div className="text-center">#</div>
          <div className="px-3">{t('presentation.reveal.team')}</div>
          <div className="text-right pr-2">{t('presentation.reveal.totalScore')}</div>
          {instances.map((inst) => (
            <div key={inst.id} className="text-center px-1 truncate" title={inst.name}>
              {inst.name}
            </div>
          ))}
        </div>
        <div className="relative" style={{ height: teams.length * ROW_HEIGHT + 4 }}>
          {teams.map((tm) => {
            const key = teamScoreKey(tm);
            const rank = rankByKey.get(key) ?? 0;
            const medal = rank === 0 ? 'gold' : rank === 1 ? 'silver' : rank === 2 ? 'bronze' : null;
            return (
              <div
                key={key}
                className={`absolute left-0 right-0 grid items-center rounded-lg my-0.5 transition-[transform,background-color] duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${
                  medal === 'gold' ? 'bg-amber-400/15 ring-1 ring-amber-300/40'
                  : medal === 'silver' ? 'bg-zinc-300/10 ring-1 ring-zinc-300/30'
                  : medal === 'bronze' ? 'bg-amber-700/10 ring-1 ring-amber-600/30'
                  : 'bg-white/5'
                }`}
                style={{
                  transform: `translateY(${rank * ROW_HEIGHT}px)`,
                  height: ROW_HEIGHT - 4,
                  gridTemplateColumns: `48px minmax(180px, 1fr) 110px repeat(${instances.length}, minmax(72px, 1fr))`,
                }}
              >
                <div className="text-center font-mono text-lg font-bold tabular-nums">
                  {medal === 'gold' ? '🥇' : medal === 'silver' ? '🥈' : medal === 'bronze' ? '🥉' : rank + 1}
                </div>
                <div className="px-3 min-w-0">
                  <div className="font-semibold truncate">{tm.team_name}</div>
                  {tm.kind === 'team' && tm.members?.length > 0 && (
                    <div className="text-xs text-white/50 truncate">{tm.members.join(' · ')}</div>
                  )}
                </div>
                <div className="text-right pr-2 font-mono text-lg font-bold tabular-nums text-accent-200">
                  {formatScore(tm.total_score)}
                </div>
                {instances.map((inst) => {
                  const cell = tm.scores?.[String(inst.id)];
                  const isFlipping = flipKey && flipKey.teamKey === key && flipKey.instanceId === inst.id;
                  return (
                    <div key={inst.id} className="flex justify-center px-1">
                      <ScoringCell cell={cell} flipping={isFlipping} />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ScoringCell({ cell, flipping }) {
  if (!cell || (cell.best_score === 0 && (cell.pending_changes || 0) === 0 && (cell.submission_count || 0) === 0)) {
    return (
      <span className="w-full h-9 rounded text-xs flex items-center justify-center text-white/20">-</span>
    );
  }
  const pending = (cell.pending_changes || 0) > 0;
  const cls = pending
    ? 'bg-sky-500/25 text-sky-100 ring-1 ring-sky-400/40'
    : cell.best_score > 0
      ? 'bg-emerald-500/15 text-emerald-100 ring-1 ring-emerald-400/30'
      : 'bg-white/5 text-white/40 ring-1 ring-white/10';
  return (
    <span
      className={`w-full h-9 rounded text-xs font-mono flex items-center justify-center transition-transform duration-150 ${cls} ${
        flipping ? 'scale-y-0' : 'scale-y-100'
      }`}
      style={flipping ? { transitionDuration: `${REVEAL_FLIP_MS / 2}ms` } : undefined}
    >
      <span className="font-bold tabular-nums truncate px-1">
        {pending && cell.best_score === 0 ? '?' : formatScore(cell.best_score)}
        {pending && cell.best_score > 0 && <span className="text-sky-200/80 ml-0.5">+?</span>}
      </span>
    </span>
  );
}

function BestScoreOverlay({ announcement }) {
  const { t } = useTranslation();
  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none animate-fade-in">
      <div className="bg-zinc-900/90 border border-amber-300/40 rounded-lg px-12 py-8 shadow-2xl shadow-amber-500/30 max-w-2xl text-center">
        <div className="text-amber-300 text-sm uppercase tracking-widest font-bold mb-2 flex items-center justify-center gap-2">
          🏆 {t('presentation.bestScore.heading')}
        </div>
        <div className="inline-block px-6 py-2 rounded-lg bg-accent-500/30 text-accent-100 text-2xl font-bold mb-3">
          {announcement.instanceName}
        </div>
        <div className="text-3xl font-bold mt-2">{announcement.team_name}</div>
        {announcement.members?.length > 0 && (
          <div className="text-white/60 text-sm mt-1">{announcement.members.join(' · ')}</div>
        )}
        <div className="text-amber-300 text-2xl font-mono mt-3 tabular-nums">
          {formatScore(announcement.score)}
        </div>
      </div>
    </div>
  );
}
