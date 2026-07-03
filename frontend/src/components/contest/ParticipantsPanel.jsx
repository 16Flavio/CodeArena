import { useState } from 'react';
import { Users, ChevronDown, ChevronUp, CheckCircle, Ban } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { listContestRegistrations, setRegistrationDisqualified } from '../../api';
import { usePrompt } from '../Confirm';
import { extractErrorMessage } from '../../utils/apiError';

// Participants list — visible to everyone who can see the contest, even if
// they haven't registered themselves. Collapsed by default. The list itself
// lives in the parent (registration refreshes it too); admins can
// disqualify/requalify entries inline.
export default function ParticipantsPanel({ contestId, participants, setParticipants, isAdmin }) {
  const { t } = useTranslation();
  const prompt = usePrompt();
  const [showParticipants, setShowParticipants] = useState(false);

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setShowParticipants(!showParticipants)}
        className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors dark:hover:bg-slate-800/30"
      >
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
          <Users className="w-5 h-5 text-violet-500 dark:text-violet-400" />
          {t('contest.participants')}
          <span className="text-xs font-normal text-slate-400 ml-1 dark:text-gray-500">
            ({participants.length})
          </span>
        </h2>
        {showParticipants ? (
          <ChevronUp className="w-5 h-5 text-slate-400 dark:text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400 dark:text-gray-400" />
        )}
      </button>
      {showParticipants && (
        <div className="px-5 pb-5">
          {participants.length === 0 ? (
            <p className="text-sm text-slate-400 italic dark:text-gray-600">
              {t('contest.noParticipants')}
            </p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {participants.map((p) => (
                <div
                  key={p.id}
                  className={`flex items-center gap-2 py-2 px-3 rounded-lg bg-white border dark:bg-slate-700/20 ${
                    p.disqualified
                      ? 'border-red-500/40 opacity-70'
                      : 'border-gray-200 dark:border-transparent'
                  }`}
                  title={p.disqualified ? p.disqualified_reason || t('contest.disqualified') : undefined}
                >
                  {p.kind === 'team' ? (
                    <>
                      <Users className="w-4 h-4 text-violet-500 flex-shrink-0 dark:text-violet-400" />
                      <span className={`text-sm truncate ${p.disqualified ? 'line-through text-slate-400 dark:text-gray-500' : 'text-slate-700 dark:text-gray-200'}`}>
                        {p.team_name}
                      </span>
                    </>
                  ) : (
                    <>
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500/30 to-indigo-500/30 flex items-center justify-center text-xs font-bold text-violet-700 flex-shrink-0 dark:text-violet-300">
                        {(p.username || '?')[0].toUpperCase()}
                      </div>
                      <span className={`text-sm truncate ${p.disqualified ? 'line-through text-slate-400 dark:text-gray-500' : 'text-slate-700 dark:text-gray-200'}`}>
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
                          // ``prompt`` returns null on cancel — stop without DQing.
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
                          : 'text-slate-400 hover:text-red-500 hover:bg-red-500/10 dark:text-gray-500'
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
