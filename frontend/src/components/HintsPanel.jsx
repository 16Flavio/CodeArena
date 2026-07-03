import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Lightbulb, Lock, Unlock } from 'lucide-react';
import { listHints, unlockHint } from '../api';
import { useConfirm } from './Confirm';
import { extractErrorMessage } from '../utils/apiError';

export default function HintsPanel({ contestId }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [hints, setHints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(null);

  const refresh = () =>
    listHints(contestId)
      .then((r) => setHints(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  const handleUnlock = async (hint) => {
    const pct = Math.round((hint.cost_fraction || 0) * 100);
    const ok = await confirm({
      message: t('hints.confirmUnlock', { label: hint.label, pct }),
    });
    if (!ok) return;
    setUnlocking(hint.id);
    try {
      await unlockHint(hint.id);
      await refresh();
      toast.success(t('hints.unlocked'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('hints.unlockFailed')));
    } finally {
      setUnlocking(null);
    }
  };

  if (loading || hints.length === 0) return null;

  return (
    <div className="glass-card p-6">
      <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2 dark:text-white">
        <Lightbulb className="w-5 h-5 text-amber-500 dark:text-amber-400" />
        {t('hints.title')}
      </h2>
      <ul className="space-y-2">
        {hints.map((h) => {
          const pct = Math.round((h.cost_fraction || 0) * 100);
          return (
            <li
              key={h.id}
              className="rounded-lg border border-gray-200 p-3 dark:border-slate-700/50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {h.unlocked ? (
                      <Unlock className="w-4 h-4 text-emerald-500 flex-shrink-0 dark:text-emerald-400" />
                    ) : (
                      <Lock className="w-4 h-4 text-slate-400 flex-shrink-0 dark:text-gray-500" />
                    )}
                    <span className="text-sm font-medium text-slate-900 dark:text-white">
                      {h.label || `#${h.id}`}
                    </span>
                    <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-400">
                      -{pct}%
                    </span>
                  </div>
                  {h.unlocked && h.body && (
                    <p className="text-sm text-slate-700 whitespace-pre-wrap mt-2 dark:text-gray-200">
                      {h.body}
                    </p>
                  )}
                </div>
                {!h.unlocked && (
                  <button
                    type="button"
                    onClick={() => handleUnlock(h)}
                    disabled={unlocking === h.id}
                    className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-50"
                  >
                    {unlocking === h.id ? t('hints.unlocking') : t('hints.unlock')}
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
