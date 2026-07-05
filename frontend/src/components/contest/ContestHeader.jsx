import { Clock, Link2, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { copyText } from '../../utils/clipboard';
import { formatCountdown, formatDateTime, backendIsoMs } from '../../utils/datetime';

// Meta strip that sits right under the PageHeader: live/ended/upcoming
// badge, start/end times with a live countdown, and the copy-link action.
// Title, description and the scoreboard link moved up into the PageHeader.
export default function ContestHeader({ contest, now }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
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
      {contest.start_time && (
        <span className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
          <Clock className="w-3.5 h-3.5" />
          {t('contest.startLabel')}{' '}
          <span className="font-mono tabular-nums text-zinc-700 dark:text-zinc-300">
            {formatDateTime(contest.start_time)}
          </span>
        </span>
      )}
      {contest.end_time && (
        <span className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
          <Clock className="w-3.5 h-3.5" />
          {t('contest.endLabel')}{' '}
          <span className="font-mono tabular-nums text-zinc-700 dark:text-zinc-300">
            {formatDateTime(contest.end_time)}
          </span>
          {backendIsoMs(contest.end_time) > now && (
            <span className="font-mono tabular-nums text-zinc-500 dark:text-zinc-400">
              {t('contest.endingIn', {
                remaining: formatCountdown((backendIsoMs(contest.end_time) - now) / 1000),
              })}
            </span>
          )}
        </span>
      )}
      {contest.max_team_size != null && contest.participation_mode !== 'solo' && (
        <span className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
          <Users className="w-3.5 h-3.5" />
          {t('contest.maxTeamSize', { count: contest.max_team_size })}
        </span>
      )}
      <button
        type="button"
        onClick={async () => {
          const ok = await copyText(window.location.href);
          if (ok) toast.success(t('contest.toastLinkCopied'));
          else toast.error(t('contest.toastLinkCopyFailed'));
        }}
        className="ml-auto flex items-center gap-1.5 font-medium text-zinc-500 hover:text-zinc-900 transition-colors dark:text-zinc-400 dark:hover:text-zinc-100"
        title={t('contest.copyLink')}
      >
        <Link2 className="w-3.5 h-3.5" />
        {t('contest.copyLink')}
      </button>
    </div>
  );
}
