import { CheckCircle, AlertCircle, Lock, Ban } from 'lucide-react';
import { useTranslation } from 'react-i18next';

// Registration panel — shown before/after the submit card to give the user
// an explicit Register/Unregister control (or the ban notice). Admins never
// need to register, so the parent only renders this for non-admins.
export default function RegistrationPanel({
  registration, isBanned, registering, teams, selectedTeam, setSelectedTeam,
  participationMode, onRegister, onUnregister,
}) {
  const { t } = useTranslation();

  if (isBanned) {
    return (
      <div className="card p-4 border border-red-500/40 bg-red-500/5 dark:bg-red-500/10">
        <div className="flex items-start gap-3">
          <Ban className="w-6 h-6 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-red-700 dark:text-red-300">
              {t('contest.bannedTitle')}
            </h3>
            <p className="text-sm text-red-700/90 dark:text-red-200/90 mt-1">
              {registration.disqualified_reason || t('contest.bannedReasonNone')}
            </p>
            <p className="text-xs text-red-700/70 dark:text-red-200/70 mt-2">
              {t('contest.bannedHelp')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-4 flex items-center justify-between gap-3 flex-wrap">
      <div className="flex items-center gap-2 text-sm">
        {registration.registered ? (
          <>
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <span className="text-zinc-700 dark:text-zinc-200 font-medium">
              {registration.kind === 'team'
                ? t('contest.registeredAsTeam')
                : t('contest.registeredAsSolo')}
            </span>
          </>
        ) : registration.can_register ? (
          <>
            <AlertCircle className="w-5 h-5 text-amber-500" />
            <span className="text-zinc-700 dark:text-zinc-200">
              {t('contest.registerToSubmit')}
            </span>
          </>
        ) : (
          <>
            <Lock className="w-5 h-5 text-zinc-400" />
            <span className="text-zinc-500 dark:text-zinc-400">
              {registration.reason || t('contest.cannotRegister')} —{' '}
              {t('contest.scoreboardOnly')}
            </span>
          </>
        )}
      </div>
      {registration.registered ? (
        <button
          type="button"
          onClick={onUnregister}
          disabled={registering}
          className="btn-secondary text-sm py-2 px-3 disabled:opacity-50"
        >
          {registering ? t('contest.registering') : t('contest.unregister')}
        </button>
      ) : registration.can_register ? (
        participationMode === 'both' ? (
          <div className="flex items-center gap-2 flex-wrap">
            {teams.length > 0 && (
              <>
                <select
                  className="input-field text-sm py-1.5"
                  value={selectedTeam || ''}
                  onChange={(e) => setSelectedTeam(e.target.value ? parseInt(e.target.value, 10) : '')}
                >
                  <option value="">{t('contest.pickTeam')}</option>
                  {teams.map((tm) => (
                    <option key={tm.id} value={tm.id}>{tm.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => onRegister('team')}
                  disabled={registering || !selectedTeam}
                  className="btn-primary text-sm py-2 px-3 disabled:opacity-50"
                  title={t('contest.registerAsTeamTitle')}
                >
                  {registering ? t('contest.registering') : t('contest.registerAsTeam')}
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => onRegister('solo')}
              disabled={registering}
              className="btn-secondary text-sm py-2 px-3 disabled:opacity-50"
              title={t('contest.registerSoloTitle')}
            >
              {t('contest.registerSolo')}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onRegister()}
            disabled={registering}
            className="btn-primary text-sm py-2 px-3 disabled:opacity-50"
          >
            {registering ? t('contest.registering') : t('contest.register')}
          </button>
        )
      ) : null}
    </div>
  );
}
