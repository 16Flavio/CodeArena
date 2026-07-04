// Admin-only: per-problem / per-language / per-verdict counts + a
// one-click link to the CLICS event feed. Loads lazily when the admin
// opens the panel (no auto-refresh; the operator hits "Refresh" if they
// want fresher numbers).
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { BarChart3, Download, RefreshCw } from 'lucide-react';
import api, { getIcpcStats } from '../api';
import { extractErrorMessage } from '../utils/apiError';

export default function IcpcStatsPanel({ contestId }) {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = () => {
    setLoading(true);
    getIcpcStats(contestId)
      .then((r) => setStats(r.data))
      .catch((err) => toast.error(extractErrorMessage(err, 'Failed to load stats')))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [contestId]);

  const downloadFeed = async () => {
    try {
      // Fetch through axios so the Authorization header is applied, then
      // trigger a client-side download. Anchor tags can't attach headers,
      // so this is the cleanest way to use the admin's token.
      const r = await api.get(`/contests/${contestId}/event-feed`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `contest-${contestId}-event-feed.ndjson`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Failed to download event feed'));
    }
  };

  return (
    <div className="bg-white/70 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent-500 dark:text-accent-400" />
          {t('icpcStats.heading')}
        </h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={downloadFeed}
            className="btn-secondary text-xs py-1 px-2 inline-flex items-center gap-1"
            title={t('icpcStats.eventFeedHint')}
          >
            <Download className="w-3.5 h-3.5" /> {t('icpcStats.eventFeed')}
          </button>
          <button
            type="button"
            className="btn-secondary text-xs py-1 px-2 inline-flex items-center gap-1"
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </div>

      {!stats ? (
        <p className="text-xs text-zinc-400 dark:text-zinc-500">{loading ? t('common.loading') : '-'}</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-zinc-50 dark:bg-zinc-900/40 rounded p-2">
              <div className="text-zinc-500 dark:text-zinc-400 uppercase text-[10px]">
                {t('icpcStats.totalSubmissions')}
              </div>
              <div className="text-xl font-bold text-zinc-800 dark:text-white">
                {stats.total_submissions}
              </div>
            </div>
            <div className="bg-zinc-50 dark:bg-zinc-900/40 rounded p-2">
              <div className="text-zinc-500 dark:text-zinc-400 uppercase text-[10px]">
                {t('icpcStats.totalTeams')}
              </div>
              <div className="text-xl font-bold text-zinc-800 dark:text-white">
                {stats.total_teams}
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-[11px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
              {t('icpcStats.perProblem')}
            </h4>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 dark:text-zinc-400">
                  <th className="text-left">{t('icpcStats.label')}</th>
                  <th className="text-left">{t('icpcStats.name')}</th>
                  <th className="text-right">{t('icpcStats.submissions')}</th>
                  <th className="text-right">{t('icpcStats.accepted')}</th>
                  <th className="text-right">{t('icpcStats.firstSolve')}</th>
                </tr>
              </thead>
              <tbody>
                {stats.per_problem.map((p) => (
                  <tr key={p.problem_id} className="border-t border-zinc-200/60 dark:border-zinc-700/60">
                    <td className="font-mono">{p.label}</td>
                    <td>{p.name}</td>
                    <td className="text-right font-mono">{p.submissions}</td>
                    <td className="text-right font-mono">{p.accepted}</td>
                    <td className="text-right font-mono">
                      {p.first_solve_minutes == null ? '-' : `${p.first_solve_minutes}'`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-[11px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
                {t('icpcStats.perLanguage')}
              </h4>
              <table className="w-full text-xs">
                <thead><tr className="text-zinc-500 dark:text-zinc-400">
                  <th className="text-left">{t('icpcStats.language')}</th>
                  <th className="text-right">{t('icpcStats.submissions')}</th>
                  <th className="text-right">{t('icpcStats.accepted')}</th>
                </tr></thead>
                <tbody>
                  {stats.per_language.map((l) => (
                    <tr key={l.language_id} className="border-t border-zinc-200/60 dark:border-zinc-700/60">
                      <td className="font-mono">{l.language_id}</td>
                      <td className="text-right font-mono">{l.submissions}</td>
                      <td className="text-right font-mono">{l.accepted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h4 className="text-[11px] uppercase text-zinc-500 dark:text-zinc-400 mb-1">
                {t('icpcStats.perVerdict')}
              </h4>
              <table className="w-full text-xs">
                <thead><tr className="text-zinc-500 dark:text-zinc-400">
                  <th className="text-left">{t('icpcStats.verdict')}</th>
                  <th className="text-right">{t('icpcStats.count')}</th>
                </tr></thead>
                <tbody>
                  {stats.per_verdict.map((v) => (
                    <tr key={v.verdict} className="border-t border-zinc-200/60 dark:border-zinc-700/60">
                      <td className="font-mono">{v.verdict}</td>
                      <td className="text-right font-mono">{v.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
