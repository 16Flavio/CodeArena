import { useEffect, useMemo, useState } from 'react';
import { Play, Pause, RotateCcw, ChevronsRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// Sorting algorithms - yield steps. Each step is a snapshot of the array
// plus indices being compared / swapped, so the widget can paint the
// state at any time. Keep these pure: no DOM, no React. The animation
// loop pulls one step at a time on a timer. Adding a new algo = add a
// generator to ALGOS - the directive type is the key.

function* bubbleSort(arr) {
  const a = [...arr];
  yield { array: [...a], compare: [], swap: [], note: 'init' };
  for (let i = 0; i < a.length - 1; i++) {
    for (let j = 0; j < a.length - i - 1; j++) {
      yield { array: [...a], compare: [j, j + 1], swap: [], note: `compare ${j} & ${j + 1}` };
      if (a[j] > a[j + 1]) {
        [a[j], a[j + 1]] = [a[j + 1], a[j]];
        yield { array: [...a], compare: [], swap: [j, j + 1], note: `swap ${j} & ${j + 1}` };
      }
    }
  }
  yield { array: [...a], compare: [], swap: [], note: 'done' };
}

function* insertionSort(arr) {
  const a = [...arr];
  yield { array: [...a], compare: [], swap: [], note: 'init' };
  for (let i = 1; i < a.length; i++) {
    let j = i;
    while (j > 0) {
      yield { array: [...a], compare: [j - 1, j], swap: [], note: `compare ${j - 1} & ${j}` };
      if (a[j - 1] <= a[j]) break;
      [a[j - 1], a[j]] = [a[j], a[j - 1]];
      yield { array: [...a], compare: [], swap: [j - 1, j], note: `swap ${j - 1} & ${j}` };
      j--;
    }
  }
  yield { array: [...a], compare: [], swap: [], note: 'done' };
}

function* selectionSort(arr) {
  const a = [...arr];
  yield { array: [...a], compare: [], swap: [], note: 'init' };
  for (let i = 0; i < a.length - 1; i++) {
    let minIdx = i;
    for (let j = i + 1; j < a.length; j++) {
      yield { array: [...a], compare: [minIdx, j], swap: [], note: `compare min=${minIdx} & ${j}` };
      if (a[j] < a[minIdx]) minIdx = j;
    }
    if (minIdx !== i) {
      [a[i], a[minIdx]] = [a[minIdx], a[i]];
      yield { array: [...a], compare: [], swap: [i, minIdx], note: `swap ${i} & ${minIdx}` };
    }
  }
  yield { array: [...a], compare: [], swap: [], note: 'done' };
}

const ALGOS = {
  bubble: bubbleSort,
  insertion: insertionSort,
  selection: selectionSort,
};

const TICK_MS = 600; // step duration when playing

/**
 * `:::viz-sort{algo="bubble" data="[5,2,8,1,9,3]"}`
 *
 * Renders an SVG bar-chart of the array and animates a chosen sort.
 * The directive's attributes are the props ``algo`` and ``data``.
 *
 * data is parsed as JSON. If it's malformed or the algo is unknown we
 * render a small inline error rather than crashing the lesson.
 */
export default function SortViz({ algo = 'bubble', data = '[5,2,8,1,9,3]' }) {
  const { t } = useTranslation();
  const parsed = useMemo(() => {
    try {
      const v = JSON.parse(data);
      if (!Array.isArray(v) || !v.every((n) => typeof n === 'number')) return null;
      return v.slice(0, 24); // safety cap on input size
    } catch {
      return null;
    }
  }, [data]);
  const generator = ALGOS[algo];
  const valid = parsed && generator;

  // Materialise all steps in a memo - derived from the inputs, no
  // ref involved. Reading a useRef during render is now flagged by
  // react-hooks/refs (and rightfully so: refs aren't reactive). The
  // memo value IS reactive on (parsed, generator) which is what we
  // want.
  const steps = useMemo(() => {
    if (!valid) return [];
    return Array.from(generator(parsed));
  }, [parsed, generator, valid]);

  const [stepIdx, setStepIdx] = useState(0);
  const [playing, setPlaying] = useState(false);

  // Reset the playhead when the steps array changes (new algo / new
  // data). React-hooks 7+ warns on setState-in-effect; left as a
  // warning project-wide. The pattern is intentional here - stepIdx
  // is genuinely stateful (the user scrubs / plays).
  useEffect(() => {
    setStepIdx(0);
    setPlaying(false);
  }, [steps]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setStepIdx((i) => {
        if (i >= steps.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [playing, steps.length]);

  if (!valid) {
    return (
      <div className="my-4 p-3 rounded-lg border border-red-300 bg-red-50 text-sm text-red-700 dark:bg-red-950/30 dark:border-red-800 dark:text-red-300">
        {t('learn.widget.sortInvalid', { algo, data })}
      </div>
    );
  }

  const step = steps[stepIdx] ?? { array: parsed, compare: [], swap: [], note: '' };
  const max = Math.max(...step.array, 1);

  return (
    <div className="my-6 not-prose rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700/50 dark:bg-zinc-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wide font-semibold text-accent-600 dark:text-accent-400">
          {t('learn.widget.sortTitle')} · {algo}
        </div>
        <div className="text-xs text-zinc-400 dark:text-zinc-500">
          {t('learn.widget.step', { current: stepIdx + 1, total: steps.length })}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${step.array.length * 40} 200`}
        className="w-full h-48"
        preserveAspectRatio="xMidYMid meet"
      >
        {step.array.map((value, idx) => {
          const isCompare = step.compare.includes(idx);
          const isSwap = step.swap.includes(idx);
          const fill = isSwap
            ? '#f97316'
            : isCompare
              ? '#2f9a8d'
              : '#8ba39d';
          const h = (value / max) * 160;
          return (
            <g key={idx} style={{ transition: 'transform 300ms ease' }}>
              <rect
                x={idx * 40 + 4}
                y={200 - h - 20}
                width={32}
                height={h}
                rx={4}
                fill={fill}
                style={{ transition: 'y 300ms ease, height 300ms ease, fill 200ms ease' }}
              />
              <text
                x={idx * 40 + 20}
                y={195}
                textAnchor="middle"
                className="fill-zinc-600 dark:fill-zinc-400"
                fontSize="12"
              >
                {value}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="flex items-center justify-center gap-2 mt-3">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="p-2 rounded-lg bg-accent-500 text-white hover:bg-accent-600 transition-colors"
          aria-label={playing ? t('learn.widget.pause') : t('learn.widget.play')}
        >
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
        <button
          onClick={() => {
            setPlaying(false);
            setStepIdx((i) => Math.min(steps.length - 1, i + 1));
          }}
          className="p-2 rounded-lg bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-600 transition-colors"
          aria-label={t('learn.widget.stepNext')}
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setPlaying(false);
            setStepIdx(0);
          }}
          className="p-2 rounded-lg bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-600 transition-colors"
          aria-label={t('learn.widget.reset')}
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
