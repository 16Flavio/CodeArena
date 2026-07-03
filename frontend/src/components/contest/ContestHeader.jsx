import { Link } from 'react-router-dom';
import { Clock, Trophy, Link2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { copyText } from '../../utils/clipboard';
import { formatCountdown, formatDateTime, backendIsoMs } from '../../utils/datetime';

// Contest title, live/ended/upcoming badge, start/end times, and the
// copy-link + scoreboard actions.
export default function ContestHeader({ contest, now }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <h1 className="text-3xl font-bold text-slate-900 break-words dark:text-white">{contest.title}</h1>
          {contest.is_open_for_submissions ? (
            <span className="badge-active">{t('contest.statusLive')}</span>
          ) : contest.end_time && backendIsoMs(contest.end_time) <= now ? (
            <span className="badge-inactive">{t('contest.statusEnded')}</span>
          ) : contest.start_time && backendIsoMs(contest.start_time) > now ? (
            <span className="badge bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300">
              {t('contest.statusUpcoming')}
            </span>
          ) : (
            <span className="badge-inactive">{t('contest.statusClosed')}</span>
          )}
        </div>
        <p className="text-slate-500 dark:text-gray-400">{contest.description}</p>
        <div className="text-xs text-slate-400 mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 dark:text-gray-500">
          {contest.start_time && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {t('contest.startLabel')} {formatDateTime(contest.start_time)}
            </span>
          )}
          {contest.end_time && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {t('contest.endLabel')} {formatDateTime(contest.end_time)}
              {backendIsoMs(contest.end_time) > now && (
                <span className="text-slate-500 dark:text-gray-400">
                  {t('contest.endingIn', {
                    remaining: formatCountdown((backendIsoMs(contest.end_time) - now) / 1000),
                  })}
                </span>
              )}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={async () => {
            const ok = await copyText(window.location.href);
            if (ok) toast.success(t('contest.toastLinkCopied'));
            else toast.error(t('contest.toastLinkCopyFailed'));
          }}
          className="btn-secondary text-sm"
          title={t('contest.copyLink')}
        >
          <Link2 className="w-4 h-4 mr-2 inline" />
          {t('contest.copyLink')}
        </button>
        <Link to={`/scoreboard/${contest.id}`} className="btn-secondary text-sm">
          <Trophy className="w-4 h-4 mr-2 inline" />
          {t('contest.scoreboard')}
        </Link>
      </div>
    </div>
  );
}
