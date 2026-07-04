import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Users, UserPlus, UserMinus } from 'lucide-react';
import {
  listContestParticipants, addContestParticipantUser, addContestParticipantTeam,
  removeContestParticipant, browseTeams,
} from '../../api';
import { extractErrorMessage } from '../../utils/apiError';

// Allowlist editor for private contests: add/remove user or team
// entries depending on the participation mode. Only mounted while the
// section is visible (edit mode + private access), so it fetches its
// own participant list on mount. ``users`` comes from Admin.jsx, which
// already has the full list loaded for the Users tab.
export default function ParticipantsAllowlist({ contest, participationMode, users }) {
  const { t } = useTranslation();
  const [participants, setParticipants] = useState([]);
  const [participantUserId, setParticipantUserId] = useState('');
  const [participantTeamId, setParticipantTeamId] = useState('');
  const [allTeams, setAllTeams] = useState([]);

  const refreshParticipants = async (contestId) => {
    try {
      const [pRes, tRes] = await Promise.all([
        listContestParticipants(contestId),
        browseTeams(),
      ]);
      setParticipants(pRes.data);
      setAllTeams(tRes.data || []);
    } catch {
      setParticipants([]);
    }
  };

  useEffect(() => {
    // Loading on (re)mount is intentional - the setState inside
    // ``refreshParticipants`` is the whole point.
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    refreshParticipants(contest.id);
  }, [contest.id]);

  const handleAddParticipantUser = async () => {
    if (!contest || !participantUserId) return;
    try {
      await addContestParticipantUser(contest.id, parseInt(participantUserId, 10));
      toast.success(t('admin.form.toastParticipantAdded'));
      setParticipantUserId('');
      refreshParticipants(contest.id);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastParticipantAddFailed')));
    }
  };

  const handleAddParticipantTeam = async () => {
    if (!contest || !participantTeamId) return;
    try {
      await addContestParticipantTeam(contest.id, parseInt(participantTeamId, 10));
      toast.success(t('admin.form.toastParticipantAdded'));
      setParticipantTeamId('');
      refreshParticipants(contest.id);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastParticipantAddFailed')));
    }
  };

  const handleRemoveParticipant = async (entryId) => {
    if (!contest) return;
    try {
      await removeContestParticipant(contest.id, entryId);
      toast.success(t('admin.form.toastParticipantRemoved'));
      refreshParticipants(contest.id);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.form.toastParticipantRemoveFailed')));
    }
  };

  return (
    <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 space-y-3 dark:bg-zinc-800/30 dark:border-zinc-700/40">
      <label className="block text-sm font-medium text-zinc-700 flex items-center gap-2 dark:text-zinc-300">
        <Users className="w-4 h-4 text-accent-500 dark:text-accent-400" />
        {t('admin.form.allowlistLabel')}
        <span className="text-xs font-normal text-zinc-400 dark:text-zinc-500">
          ({participants.length})
        </span>
      </label>

      {(participationMode === 'team'
        || participationMode === 'both') && (
        <div className="flex gap-2">
          <select
            className="input-field text-sm py-2 flex-1"
            value={participantTeamId}
            onChange={(e) => setParticipantTeamId(e.target.value)}
          >
            <option value="">{t('admin.form.allowlistPickTeam')}</option>
            {allTeams
              .filter((tm) => !participants.some((p) => p.kind === 'team' && p.team_id === tm.id))
              .map((tm) => (
                <option key={tm.id} value={tm.id}>
                  {tm.name}
                </option>
              ))}
          </select>
          <button
            type="button"
            onClick={handleAddParticipantTeam}
            disabled={!participantTeamId}
            className="btn-primary text-sm py-2 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <UserPlus className="w-4 h-4 mr-1 inline" />
            {t('admin.form.allowlistAddTeam')}
          </button>
        </div>
      )}

      {(participationMode === 'solo'
        || participationMode === 'both') && (
        <div className="flex gap-2">
          <select
            className="input-field text-sm py-2 flex-1"
            value={participantUserId}
            onChange={(e) => setParticipantUserId(e.target.value)}
          >
            <option value="">{t('admin.form.allowlistPickUser')}</option>
            {users
              .filter((u) => !participants.some((p) => p.kind === 'user' && p.user_id === u.id))
              .map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username} ({u.email})
                </option>
              ))}
          </select>
          <button
            type="button"
            onClick={handleAddParticipantUser}
            disabled={!participantUserId}
            className="btn-primary text-sm py-2 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <UserPlus className="w-4 h-4 mr-1 inline" />
            {t('admin.form.allowlistAddUser')}
          </button>
        </div>
      )}

      {participants.length === 0 ? (
        <p className="text-xs text-zinc-400 italic dark:text-zinc-600">
          {t('admin.form.allowlistEmpty')}
        </p>
      ) : (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {participants.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-white border border-zinc-200 dark:bg-zinc-700/20 dark:border-transparent"
            >
              <div className="text-sm text-zinc-700 dark:text-zinc-200">
                {p.kind === 'team' ? (
                  <span className="font-medium">
                    <Users className="w-3.5 h-3.5 inline mr-1 text-accent-500" />
                    {p.team_name}
                    <span className="text-xs text-zinc-400 ml-2 dark:text-zinc-500">
                      ({t('admin.form.allowlistTeamBadge')})
                    </span>
                  </span>
                ) : (
                  <>
                    <span className="font-medium">{p.username}</span>
                    <span className="text-xs text-zinc-400 ml-2 dark:text-zinc-500">
                      {p.email}
                    </span>
                  </>
                )}
              </div>
              <button
                type="button"
                onClick={() => handleRemoveParticipant(p.id)}
                className="p-1 rounded hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-500 dark:hover:text-red-400"
                title={t('admin.form.allowlistRemove')}
              >
                <UserMinus className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
