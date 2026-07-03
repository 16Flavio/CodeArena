// Admin-only: live snapshot of the RQ scoring workers + queue depth,
// plus a button to re-enqueue failed jobs. Scaling the number of
// workers is still a compose concern (SCORING_WORKER_REPLICAS in .env),
// but admins can see from here whether submissions have a consumer.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Cpu, RefreshCw } from 'lucide-react';
import { getScoringWorkers, requeueFailedJobs } from '../api';
import { formatDateTime } from '../utils/datetime';
import { extractErrorMessage } from '../utils/apiError';

export default function WorkersPanel() {
  const { t } = useTranslation();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [requeuing, setRequeuing] = useState(false);

  const refresh = () => {
    setLoading(true);
    getScoringWorkers()
      .then((r) => setState(r.data))
      .catch((err) => toast.error(extractErrorMessage(err, t('workers.loadFailed'))))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    // Auto-refresh every 5s so a just-started worker appears without a
    // manual reload. Stops when the tab unmounts.
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doRequeue = async () => {
    setRequeuing(true);
    try {
      const r = await requeueFailedJobs();
      toast.success(t('workers.requeueFailedOk', { n: r.data?.requeued ?? 0 }));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('workers.loadFailed')));
    } finally {
      setRequeuing(false);
    }
  };

  const workers = state?.workers || [];
  const q = state?.queue || {};
  const queuePills = [
    { k: 'pending', v: q.pending, cls: 'bg-zinc-500/10 text-zinc-700 dark:text-zinc-300' },
    { k: 'started', v: q.started, cls: 'bg-amber-500/10 text-amber-700 dark:text-amber-300' },
    { k: 'finished', v: q.finished, cls: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
    { k: 'failed', v: q.failed, cls: 'bg-red-500/10 text-red-700 dark:text-red-300' },
  ];

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-zinc-800 dark:text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-accent-500 dark:text-accent-400" />
          {t('workers.heading')}
          <span className="text-xs font-normal text-zinc-400 dark:text-zinc-500">
            ({workers.length}{state?.mode ? ` — ${state.mode}` : ''})
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={doRequeue}
            disabled={requeuing || state?.mode !== 'redis' || !q.failed}
            className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1 inline ${requeuing ? 'animate-spin' : ''}`} />
            {t('workers.requeueFailed')}
          </button>
          <button
            type="button"
            onClick={refresh}
            className="btn-secondary text-xs py-1.5 px-3"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {state?.note && (
        <p className="text-xs text-amber-700 dark:text-amber-300">{state.note}</p>
      )}

      <div>
        <h3 className="text-[11px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
          {t('workers.queueState')}
        </h3>
        <div className="flex flex-wrap gap-2 text-[11px]">
          {queuePills.map((p) => (
            <span key={p.k} className={`px-2 py-0.5 rounded ${p.cls} font-mono`}>
              {t(`workers.${p.k}`)}: <strong>{p.v ?? 0}</strong>
            </span>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-[11px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
          {t('workers.liveWorkers')}
        </h3>
        {workers.length === 0 ? (
          <p className="text-sm text-zinc-400 dark:text-zinc-500">{t('workers.noWorkers')}</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-zinc-500 dark:text-zinc-400">
                <th className="text-left py-1 px-2">{t('workers.col_name')}</th>
                <th className="text-left py-1 px-2">{t('workers.col_state')}</th>
                <th className="text-left py-1 px-2">{t('workers.col_current_job')}</th>
                <th className="text-left py-1 px-2">{t('workers.col_last_beat')}</th>
                <th className="text-left py-1 px-2">{t('workers.col_birth')}</th>
              </tr>
            </thead>
            <tbody>
              {workers.map((w) => (
                <tr key={w.name} className="border-t border-zinc-200/60 dark:border-zinc-700/60">
                  <td className="py-1 px-2 font-mono">{w.name}</td>
                  <td className="py-1 px-2">
                    <span className={
                      w.state === 'busy' ? 'text-amber-600 dark:text-amber-400'
                      : w.state === 'idle' ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-zinc-500 dark:text-zinc-400'
                    }>{w.state}</span>
                  </td>
                  <td className="py-1 px-2 font-mono text-[11px]">
                    {w.current_job ? `#${w.current_job.id}` : '—'}
                  </td>
                  <td className="py-1 px-2">{w.last_heartbeat ? formatDateTime(w.last_heartbeat) : '—'}</td>
                  <td className="py-1 px-2">{w.birth_date ? formatDateTime(w.birth_date) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 p-3 text-xs">
        <p className="text-zinc-600 dark:text-zinc-300 mb-1">{t('workers.scaleNote')}</p>
        <code className="block font-mono text-[11px] bg-zinc-900/90 text-emerald-300 rounded px-2 py-1 whitespace-pre">
{`# edit /opt/codearena/.env:
SCORING_WORKER_REPLICAS=4

# then apply (permanent, survives restarts):
docker compose up -d worker`}
        </code>
        <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-500">
          {t('workers.scaleHint')}
        </p>
      </div>
    </div>
  );
}
