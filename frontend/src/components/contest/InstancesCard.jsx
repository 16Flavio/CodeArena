import { FileDown, Lock } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { downloadInstance } from '../../api';
import { formatCountdown, backendIsoMs } from '../../utils/datetime';

// Instance (input file) grid with unlock countdowns and per-instance
// download buttons.
export default function InstancesCard({ contest, now }) {
  const { t } = useTranslation();

  const handleDownload = async (instanceId, instanceName) => {
    try {
      const res = await downloadInstance(instanceId);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = res.headers['content-disposition']
        ? res.headers['content-disposition'].split('filename=')[1]?.replace(/"/g, '')
        : `${instanceName}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t('contest.toastDownloadFailed'));
    }
  };

  return (
    <div className="card p-6">
      <h2 className="text-lg font-bold text-zinc-900 mb-4 flex items-center gap-2 dark:text-white">
        <FileDown className="w-5 h-5 text-accent-500 dark:text-accent-400" />
        {t('contest.instances')}
      </h2>
      {contest.instances.length === 0 ? (
        <p className="text-zinc-500 text-center py-4 dark:text-zinc-500">{t('contest.noInstances')}</p>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {contest.instances.map((inst) => {
            const unlockMs = backendIsoMs(inst.unlock_at);
            const locked = !inst.is_unlocked;
            return (
              <div
                key={inst.id}
                className={`flex items-center justify-between p-4 rounded-lg border ${
                  locked
                    ? 'bg-amber-500/5 border-amber-500/20'
                    : 'bg-zinc-50 border-zinc-200 dark:bg-zinc-800/30 dark:border-zinc-700/30'
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 min-w-0">
                    {locked && <Lock className="w-4 h-4 text-amber-500 flex-shrink-0 dark:text-amber-400" />}
                    <p className={`font-medium truncate ${locked ? 'text-zinc-600 dark:text-zinc-400' : 'text-zinc-900 dark:text-white'}`}>
                      {inst.name}
                    </p>
                  </div>
                  {locked && unlockMs && (
                    <p className="text-xs text-amber-700 mt-1 dark:text-amber-300">
                      {unlockMs > now
                        ? t('contest.unlocksIn', { remaining: formatCountdown((unlockMs - now) / 1000) })
                        : t('contest.unlocksSoon')}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDownload(inst.id, inst.name)}
                  disabled={locked}
                  className={`p-2 rounded-lg transition-colors ${
                    locked
                      ? 'text-zinc-300 cursor-not-allowed dark:text-zinc-600'
                      : 'hover:bg-zinc-100 text-accent-500 hover:text-accent-600 dark:hover:bg-zinc-700/50 dark:text-accent-400 dark:hover:text-accent-300'
                  }`}
                  title={locked ? t('contest.locked') : t('contest.downloadInput')}
                >
                  <FileDown className="w-5 h-5" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
