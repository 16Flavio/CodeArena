import { useState } from 'react';
import { Users, ChevronDown, ChevronUp, CheckCircle, Ban } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { listContestRegistrations, setRegistrationDisqualified } from '../../api';
import { usePrompt } from '../Confirm';
import { extractErrorMessage } from '../../utils/apiError';

// Participants list - visible to everyone who can see the contest, even if
// they haven't registered themselves. Collapsed by default. The list itself
// lives in the parent (registration refreshes it too); admins can
// disqualify/requalify entries inline.
export default function ParticipantsPanel({ contestId, participants, setParticipants, isAdmin }) {
  const { t } = useTranslation();
  const prompt = usePrompt();
  const [showParticipants, setShowParticipants] = useState(false);

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setShowParticipants(!showParticipants)}
        className="w-full flex items-center justify-between p-5 hover:bg-zinc-50 transition-colors dark:hover:bg-zinc-800/30"
      >
        <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
          <Users className="w-5 h-5 text-accent-500 dark:text-accent-400" />
          {t('contest.participants')}
          <span className="text-xs font-normal text-zinc-400 ml-1 dark:text-zinc-500">
            ({participants.length})
          </span>
        </h2>
        {showParticipants ? (
          <ChevronUp className="w-5 h-5 text-zinc-400 dark:text-zinc-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-zinc-400 dark:text-zinc-400" />
        )}
      </button>
      {showParticipants && (
        <div className="px-5 pb-5">
          {participants.length === 0 ? (
            <p className="text-sm text-zinc-400 italic dark:text-zinc-600">
              {t('contest.noParticipants')}
            </p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {participants.map((p) => (
                <div
                  key={p.id}
                  className={`flex items-center gap-2 py-2 px-3 rounded-lg bg-white border dark:bg-zinc-700/20 ${
                    p.disqualified
                      ? 'border-red-500/40 opacity-70'
                      : 'border-zinc-200 dark:border-transparent'
                  }`}
                  title={p.disqualified ? p.disqualified_reason || t('contest.disqualified') : undefined}
                >
                  {p.kind === 'team' ? (
                    <>
                      <Users className="w-4 h-4 text-accent-500 flex-shrink-0 dark:text-accent-400" />
                      <span className={`text-sm truncate ${p.disqualified ? 'line-through text-zinc-400 dark:text-zinc-500' : 'text-zinc-700 dark:text-zinc-200'}`}>
                        {p.team_name}
                      </span>
                    </>
                  ) : (
                    <>
                      <div className="w-6 h-6 rounded-full bg-accent-500/20 flex items-center justify-center text-xs font-bold text-accent-700 flex-shrink-0 dark:text-accent-300">
                        {(p.username || '?')[0].toUpperCase()}
                      </div>
                      <span className={`text-sm truncate ${p.disqualified ? 'line-through text-zinc-400 dark:text-zinc-500' : 'text-zinc-700 dark:text-zinc-200'}`}>
                        {p.username}
                      </span>
                    </>
                  )}
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={async () => {
                        const next = !p.disqualified;
                        let reason = null;
                        if (next) {
                          reason = await prompt({
                            title: t('contest.disqualifyReasonTitle') || t('contest.disqualifyReasonPrompt'),
                            message: t('contest.disqualifyReasonPrompt'),
                            defaultValue: '',
                          });
                          // ``prompt`` returns null on cancel - stop without DQing.
                          if (reason === null) return;
                        }
                        try {
                          await setRegistrationDisqualified(p.id, {
                            disqualified: next,
                            reason: reason || null,
                          });
                          toast.success(next ? t('contest.toastDisqualified') : t('contest.toastRequalified'));
                          const r = await listContestRegistrations(contestId);
                          setParticipants(r.data || []);
                        } catch (err) {
                          toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
                        }
                      }}
                      className={`ml-auto p-1 rounded transition-colors ${
                        p.disqualified
                          ? 'text-emerald-500 hover:bg-emerald-500/10'
                          : 'text-zinc-400 hover:text-red-500 hover:bg-red-500/10 dark:text-zinc-500'
                      }`}
                      title={p.disqualified ? t('contest.requalify') : t('contest.disqualify')}
                      aria-label={p.disqualified ? t('contest.requalify') : t('contest.disqualify')}
                    >
                      {p.disqualified ? <CheckCircle className="w-3.5 h-3.5" /> : <Ban className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
