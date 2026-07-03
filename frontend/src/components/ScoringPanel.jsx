import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Cpu, RefreshCw, AlertCircle, Mail } from 'lucide-react';
import toast from 'react-hot-toast';
import { getScoringStats, triggerAdminDigest } from '../api';
import { formatDateTime } from '../utils/datetime';
import { extractErrorMessage } from '../utils/apiError';

export default function ScoringPanel() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    getScoringStats()
      .then((r) => setStats(r.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
          <Cpu className="w-5 h-5 text-accent-500 dark:text-accent-400" />
          {t('admin.scoring.title')}
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={async () => {
              try {
                const r = await triggerAdminDigest();
                toast.success(t('admin.scoring.digestSent', { count: r.data?.recipients || 0 }));
              } catch (err) {
                toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
              }
            }}
            className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            title={t('admin.scoring.digestHint')}
          >
            <Mail className="w-3.5 h-3.5" />
            {t('admin.scoring.sendDigest')}
          </button>
          <button type="button" onClick={refresh} className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </div>
      <p className="text-xs text-zinc-500 mb-4 dark:text-zinc-400">{t('admin.scoring.subtitle')}</p>
      {stats && (
        <>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <Stat label={t('admin.scoring.pending')} value={stats.pending} tone="amber" />
            <Stat label={t('admin.scoring.scored')} value={stats.scored} tone="emerald" />
            <Stat label={t('admin.scoring.errors')} value={stats.errors} tone="red" />
          </div>
          <h3 className="text-sm font-semibold text-zinc-900 mb-2 dark:text-white">
            {t('admin.scoring.recentErrors')}
          </h3>
          {stats.recent_errors.length === 0 ? (
            <p className="text-sm text-zinc-400 italic dark:text-zinc-500">{t('admin.scoring.noErrors')}</p>
          ) : (
            <ul className="space-y-2">
              {stats.recent_errors.map((e) => (
                <li key={e.id} className="text-xs rounded-lg border border-red-500/30 bg-red-500/5 p-3 dark:border-red-500/20">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertCircle className="w-3.5 h-3.5 text-red-500 dark:text-red-400" />
                    <span className="text-zinc-700 font-medium dark:text-zinc-200">
                      {e.contest_title} · {e.instance_name}
                    </span>
                    <span className="text-zinc-400 ml-auto dark:text-zinc-500">{formatDateTime(e.submitted_at)}</span>
                  </div>
                  {e.error_message && (
                    <pre className="font-mono text-[11px] text-zinc-500 whitespace-pre-wrap break-all dark:text-zinc-400">
                      {e.error_message}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, tone }) {
  const toneClasses = {
    amber: 'text-amber-600 dark:text-amber-400',
    emerald: 'text-emerald-600 dark:text-emerald-400',
    red: 'text-red-600 dark:text-red-400',
  }[tone];
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700/50">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${toneClasses}`}>{value}</p>
    </div>
  );
}
