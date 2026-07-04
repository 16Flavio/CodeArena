import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import {
  getMyTeams, createTeam, joinTeam, leaveTeam, deleteTeam, removeMember,
  browseTeams, requestJoin, getIncomingRequests, getOutgoingRequests,
  acceptRequest, rejectRequest, cancelRequest, regenerateJoinCode,
  setMemberPermissions, transferOwnership,
} from '../api';
import {
  Users, Plus, LogIn, Copy, UserMinus, Crown, X, Send, Check, Ban,
  MailQuestion, Clock, CheckCircle, XCircle, Search, RefreshCw, Lock, Unlock, ArrowUpRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { copyText } from '../utils/clipboard';
import { useConfirm } from '../components/Confirm';
import PageHeader from '../components/PageHeader';
import { extractErrorMessage } from '../utils/apiError';

const MAX_TEAM_SIZE = 4;

export default function Teams() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [teams, setTeams] = useState([]);
  const [browse, setBrowse] = useState([]);
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestTarget, setRequestTarget] = useState(null);
  const [requestMessage, setRequestMessage] = useState('');

  const [newName, setNewName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [browseFilter, setBrowseFilter] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  const refresh = async () => {
    try {
      const [mine, all, inc, out] = await Promise.all([
        getMyTeams(),
        browseTeams(),
        getIncomingRequests(),
        getOutgoingRequests(),
      ]);
      setTeams(mine.data);
      setBrowse(all.data);
      setIncoming(inc.data);
      setOutgoing(out.data);
    } catch {
      toast.error(t('teams.toastLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createTeam({ name: newName });
      toast.success(t('teams.toastCreated'));
      setNewName('');
      setShowCreate(false);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastCreateFailed')));
    } finally {
      setSubmitting(false);
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await joinTeam({ join_code: joinCode });
      toast.success(t('teams.toastJoined'));
      setJoinCode('');
      setShowJoin(false);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastJoinFailed')));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLeave = async (teamId) => {
    const ok = await confirm({ message: t('teams.confirmLeave'), danger: true });
    if (!ok) return;
    try {
      await leaveTeam(teamId);
      toast.success(t('teams.toastLeft'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastLeaveFailed')));
    }
  };

  const handleDelete = async (team) => {
    const confirmMsg =
      team.members.length > 1
        ? t('teams.confirmDeleteMany', { team: team.name, count: team.members.length })
        : t('teams.confirmDelete1', { team: team.name });
    const ok = await confirm({ message: confirmMsg, danger: true });
    if (!ok) return;
    try {
      await deleteTeam(team.id);
      toast.success(t('teams.toastDeleted'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastDeleteFailed')));
    }
  };

  const handleRemove = async (teamId, userId, username) => {
    const ok = await confirm({
      message: t('teams.confirmRemove', { user: username }),
      danger: true,
    });
    if (!ok) return;
    try {
      await removeMember(teamId, userId);
      toast.success(t('teams.toastRemoved'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastRemoveFailed')));
    }
  };

  const copyCode = async (code) => {
    const ok = await copyText(code);
    if (ok) toast.success(t('teams.toastCopied'));
    else toast.error(t('teams.toastCopyFailed'));
  };

  const handleTogglePermission = async (teamId, userId, canSubmit) => {
    try {
      await setMemberPermissions(teamId, userId, { can_submit: canSubmit });
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const handleTransferOwnership = async (teamId, userId, username) => {
    const ok = await confirm({
      message: t('teams.confirmTransfer', { username }),
      danger: true,
    });
    if (!ok) return;
    try {
      await transferOwnership(teamId, userId);
      toast.success(t('teams.toastTransferred', { username }));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const handleRegenerateCode = async (teamId) => {
    const ok = await confirm({ message: t('teams.confirmRegenerate') });
    if (!ok) return;
    try {
      await regenerateJoinCode(teamId);
      toast.success(t('teams.toastNewCode'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const openRequest = (team) => {
    setRequestTarget(team);
    setRequestMessage('');
    setShowRequestModal(true);
  };

  const handleSendRequest = async (e) => {
    e.preventDefault();
    if (!requestTarget) return;
    setSubmitting(true);
    try {
      await requestJoin(requestTarget.id, requestMessage.trim());
      toast.success(t('teams.toastRequestSent', { team: requestTarget.name }));
      setShowRequestModal(false);
      setRequestTarget(null);
      setRequestMessage('');
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastRequestFailed')));
    } finally {
      setSubmitting(false);
    }
  };

  const handleAccept = async (req) => {
    setPendingAction(`accept-${req.id}`);
    try {
      await acceptRequest(req.id);
      toast.success(t('teams.toastAccepted', { user: req.username, team: req.team_name }));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastAcceptFailed')));
    } finally {
      setPendingAction(null);
    }
  };

  const handleReject = async (req) => {
    setPendingAction(`reject-${req.id}`);
    try {
      await rejectRequest(req.id);
      toast.success(t('teams.toastRejected'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastRejectFailed')));
    } finally {
      setPendingAction(null);
    }
  };

  const handleCancel = async (req) => {
    const ok = await confirm({
      message: t('teams.confirmCancelRequest', { team: req.team_name }),
    });
    if (!ok) return;
    setPendingAction(`cancel-${req.id}`);
    try {
      await cancelRequest(req.id);
      toast.success(t('teams.toastCancelled'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('teams.toastCancelFailed')));
    } finally {
      setPendingAction(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const pendingOutgoing = outgoing.filter((r) => r.status === 'pending');
  const filteredBrowse = browse.filter((t) =>
    t.name.toLowerCase().includes(browseFilter.trim().toLowerCase())
  );
  // One team per person: the user can only create/join/request while they
  // are not in any team.
  const alreadyInTeam = teams.length > 0;

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader
        eyebrow={t('nav.teams')}
        title={t('teams.title')}
        description={t('teams.subtitle')}
        actions={(
          <>
            <button
              onClick={() => setShowJoin(true)}
              className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={alreadyInTeam}
              title={alreadyInTeam ? t('teams.alreadyInTeamTooltip') : undefined}
            >
              <LogIn className="w-4 h-4 mr-2 inline" />
              {t('teams.joinByCode')}
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={alreadyInTeam}
              title={alreadyInTeam ? t('teams.alreadyInTeamTooltip') : undefined}
            >
              <Plus className="w-4 h-4 mr-2 inline" />
              {t('teams.createTeam')}
            </button>
          </>
        )}
      />

      {alreadyInTeam && (
        <div className="card p-4 border border-amber-500/30 flex items-start gap-3">
          <MailQuestion className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5 dark:text-amber-400" />
          <div>
            <p className="text-sm text-zinc-700 dark:text-zinc-200">
              {t('teams.alreadyInTeamBanner')}
            </p>
          </div>
        </div>
      )}

      {incoming.length > 0 && (
        <div className="card p-5 border-accent-500/30 border">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-4 flex items-center gap-2">
            <MailQuestion className="w-4 h-4 text-accent-500 dark:text-accent-400" />
            {t('teams.incomingRequests')}
            <span className="badge bg-accent-500/15 text-accent-700 border border-accent-500/30 font-mono tabular-nums dark:bg-accent-500/20 dark:text-accent-300">
              {incoming.length}
            </span>
          </h2>
          <div className="space-y-2">
            {incoming.map((req) => (
              <div
                key={req.id}
                className="flex items-start justify-between gap-3 p-3 rounded-lg bg-zinc-50 border border-zinc-200 flex-wrap dark:bg-zinc-800/40 dark:border-zinc-700/40"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-zinc-700 dark:text-zinc-200">
                    <span className="font-semibold text-zinc-900 dark:text-white">{req.username}</span>
                    {' '}{t('teams.wantsToJoin')}{' '}
                    <span className="font-semibold text-accent-700 dark:text-accent-300">{req.team_name}</span>
                  </p>
                  {req.message ? (
                    <p className="text-xs text-zinc-500 mt-1.5 italic break-words dark:text-zinc-400">
                      &ldquo;{req.message}&rdquo;
                    </p>
                  ) : null}
                  <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                    {new Date(req.created_at).toLocaleString('fr-FR')}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAccept(req)}
                    disabled={pendingAction === `accept-${req.id}`}
                    className="text-xs font-medium px-3 py-1.5 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 dark:bg-emerald-500/15 dark:hover:bg-emerald-500/25 dark:text-emerald-300"
                  >
                    <Check className="w-3.5 h-3.5" />
                    {t('teams.accept')}
                  </button>
                  <button
                    onClick={() => handleReject(req)}
                    disabled={pendingAction === `reject-${req.id}`}
                    className="text-xs font-medium px-3 py-1.5 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-600 transition-colors flex items-center gap-1.5 disabled:opacity-50 dark:text-red-400"
                  >
                    <Ban className="w-3.5 h-3.5" />
                    {t('teams.reject')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card p-6 w-full max-w-md animate-fade-in" role="dialog" aria-modal="true">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-white">{t('teams.createModalTitle')}</h2>
              <button
                onClick={() => setShowCreate(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
                aria-label={t('common.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('teams.teamNameLabel')}
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder={t('teams.teamNamePlaceholder')}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary text-sm">
                  {t('common.cancel')}
                </button>
                <button type="submit" className="btn-primary text-sm" disabled={submitting}>
                  {submitting ? t('teams.creating') : t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showJoin && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card p-6 w-full max-w-md animate-fade-in" role="dialog" aria-modal="true">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-white">{t('teams.joinModalTitle')}</h2>
              <button
                onClick={() => setShowJoin(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
                aria-label={t('common.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleJoin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">{t('teams.joinCodeLabel')}</label>
                <input
                  type="text"
                  className="input-field font-mono tracking-widest text-center text-lg"
                  placeholder="XXXXXXXX"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  maxLength={8}
                  required
                />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowJoin(false)} className="btn-secondary text-sm">
                  {t('common.cancel')}
                </button>
                <button type="submit" className="btn-primary text-sm" disabled={submitting}>
                  {submitting ? t('teams.joinSending') : t('teams.joinSubmit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showRequestModal && requestTarget && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card p-6 w-full max-w-md animate-fade-in" role="dialog" aria-modal="true">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-white">{t('teams.requestModalTitle')}</h2>
              <button
                onClick={() => setShowRequestModal(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
                aria-label={t('common.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSendRequest} className="space-y-4">
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {t('teams.requestSubtitle', { team: requestTarget.name })
                  .replace('<b>', '')
                  .replace('</b>', '')}
              </p>
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('teams.requestMessageLabel')}
                </label>
                <textarea
                  className="input-field min-h-[90px]"
                  placeholder={t('teams.requestMessagePlaceholder')}
                  value={requestMessage}
                  onChange={(e) => setRequestMessage(e.target.value)}
                  maxLength={500}
                />
                <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
                  {requestMessage.length}/500
                </p>
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowRequestModal(false)} className="btn-secondary text-sm">
                  {t('common.cancel')}
                </button>
                <button type="submit" className="btn-primary text-sm" disabled={submitting}>
                  {submitting ? t('common.sending') : (<><Send className="w-4 h-4 mr-2 inline" />{t('teams.sendRequest')}</>)}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
          <Users className="w-4 h-4" />
          {t('teams.myTeams')}
        </h2>
        {teams.length === 0 ? (
          <div className="card p-12 text-center">
            <Users className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
            <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('teams.noTeamsHeading')}</h3>
            <p className="text-zinc-500 mb-6 dark:text-zinc-400">
              {t('teams.noTeamsBody')}
            </p>
            <div className="flex justify-center gap-3">
              <button onClick={() => setShowJoin(true)} className="btn-secondary">
                <LogIn className="w-4 h-4 mr-2 inline" />
                {t('teams.joinByCode')}
              </button>
              <button onClick={() => setShowCreate(true)} className="btn-primary">
                <Plus className="w-4 h-4 mr-2 inline" />
                {t('teams.createTeam')}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {teams.map((team) => {
              const isOwner = team.members.some(
                (m) => m.user_id === user.id && m.role === 'owner'
              );
              const hasAnyOwner = team.members.some((m) => m.role === 'owner');
              const isOrphan = !hasAnyOwner;
              const canDelete = isOwner || isOrphan;
              return (
                <div key={team.id} className="card p-6">
                  <div className="flex items-start justify-between mb-5">
                    <div>
                      <h3 className="text-xl font-bold text-zinc-900 dark:text-white">{team.name}</h3>
                      <p className="text-zinc-500 text-sm mt-1 dark:text-zinc-500">
                        <span className="font-mono tabular-nums">{team.members.length}/{MAX_TEAM_SIZE}</span>{' '}
                        {t('teams.memberCountSuffix')}
                      </p>
                    </div>
                    {isOwner && (
                      <span className="badge bg-amber-500/15 text-amber-700 border border-amber-500/30 dark:bg-amber-500/20 dark:text-amber-400">
                        <Crown className="w-3 h-3 mr-1" />
                        {t('teams.owner')}
                      </span>
                    )}
                  </div>

                  <div className="bg-zinc-100 rounded-lg p-4 mb-5 dark:bg-zinc-800/50">
                    <p className="text-xs text-zinc-500 mb-1.5 dark:text-zinc-500">{t('teams.joinCodeTitle')}</p>
                    <div className="flex items-center gap-3">
                      <code className="text-lg font-mono font-bold text-accent-700 tracking-widest flex-1 dark:text-accent-300">
                        {team.join_code}
                      </code>
                      <button
                        onClick={() => copyCode(team.join_code)}
                        className="p-2 rounded-lg hover:bg-zinc-200 text-zinc-500 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-700 dark:text-zinc-400 dark:hover:text-white"
                        title={t('teams.copyCode')}
                        aria-label={t('teams.copyCode')}
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      {isOwner && (
                        <button
                          onClick={() => handleRegenerateCode(team.id)}
                          className="p-2 rounded-lg hover:bg-zinc-200 text-zinc-500 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-700 dark:text-zinc-400 dark:hover:text-white"
                          title={t('teams.regenerateCode')}
                          aria-label={t('teams.regenerateCode')}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm font-medium text-zinc-600 mb-2 dark:text-zinc-400">{t('teams.membersHeading')}</p>
                    {team.members.map((m) => (
                      <div
                        key={m.id}
                        className="flex items-center justify-between py-2 px-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-7 h-7 rounded-lg bg-accent-500/20 flex items-center justify-center text-xs font-bold text-accent-700 dark:text-accent-300 flex-shrink-0">
                            {m.username[0].toUpperCase()}
                          </div>
                          <span className="text-sm text-zinc-700 dark:text-zinc-200 truncate">{m.username}</span>
                          {m.role === 'owner' && (
                            <Crown className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 dark:text-amber-400" />
                          )}
                          {!m.can_submit && (
                            <Lock
                              className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0 dark:text-zinc-500"
                              title="Ne peut pas soumettre"
                            />
                          )}
                        </div>
                        {isOwner && m.user_id !== user.id && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={() =>
                                handleTogglePermission(team.id, m.user_id, !m.can_submit)
                              }
                              className="p-1 rounded hover:bg-zinc-200 text-zinc-500 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-700 dark:text-zinc-400 dark:hover:text-white"
                              title={m.can_submit ? t('teams.permRevoke') : t('teams.permGrant')}
                            >
                              {m.can_submit ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                            </button>
                            <button
                              onClick={() =>
                                handleTransferOwnership(team.id, m.user_id, m.username)
                              }
                              className="p-1 rounded hover:bg-amber-500/10 text-zinc-400 hover:text-amber-500 transition-colors dark:text-zinc-500 dark:hover:text-amber-400"
                              title={t('teams.makeOwner', { username: m.username })}
                            >
                              <ArrowUpRight className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRemove(team.id, m.user_id, m.username)}
                              className="p-1 rounded hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-500 dark:hover:text-red-400"
                              title={t('teams.removeMember')}
                            >
                              <UserMinus className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 pt-4 border-t border-zinc-200 dark:border-zinc-800/50 space-y-2">
                    {isOrphan && (
                      <p className="text-xs text-amber-600 dark:text-amber-400">
                        {t('teams.orphanBanner')}
                      </p>
                    )}
                    {team.members.length > 1 && !isOrphan && (
                      <button
                        onClick={() => handleLeave(team.id)}
                        className="btn-danger text-sm w-full"
                      >
                        {t('teams.leaveTeam')}
                      </button>
                    )}
                    {canDelete && (
                      <button
                        onClick={() => handleDelete(team)}
                        className="btn-danger text-sm w-full"
                      >
                        {team.members.length > 1
                          ? t('teams.deleteTeamFull')
                          : t('teams.deleteTeam')}
                      </button>
                    )}
                    {!canDelete && team.members.length === 1 && (
                      <button
                        onClick={() => handleLeave(team.id)}
                        className="btn-danger text-sm w-full"
                      >
                        {t('teams.leaveTeam')}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {pendingOutgoing.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            {t('teams.yourPendingRequests')}
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {pendingOutgoing.map((req) => (
              <div
                key={req.id}
                className="card p-4 flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <p className="text-sm text-zinc-900 font-medium truncate dark:text-white">{req.team_name}</p>
                  <p className="text-xs text-zinc-500 mt-0.5 dark:text-zinc-500">
                    {t('teams.sentOn', { date: new Date(req.created_at).toLocaleDateString() })}
                  </p>
                </div>
                <button
                  onClick={() => handleCancel(req)}
                  disabled={pendingAction === `cancel-${req.id}`}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors disabled:opacity-50 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
                  title={t('teams.cancelAction')}
                >
                  {t('teams.cancelAction')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 flex items-center gap-2">
            <Search className="w-4 h-4" />
            {t('teams.browseTeams')}
          </h2>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none dark:text-zinc-500" />
            <input
              type="text"
              className="input-field text-sm py-2 pl-9 pr-3 w-64"
              placeholder={t('common.search')}
              value={browseFilter}
              onChange={(e) => setBrowseFilter(e.target.value)}
            />
          </div>
        </div>

        {filteredBrowse.length === 0 ? (
          <div className="card p-10 text-center">
            <Users className="w-10 h-10 text-zinc-300 mx-auto mb-3 dark:text-zinc-600" />
            <p className="text-zinc-500 dark:text-zinc-400">
              {browse.length === 0 ? t('teams.noTeamsYet') : t('teams.noBrowseResults')}
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredBrowse.map((bt) => {
              const outgoingForThis = outgoing.find(
                (r) => r.team_id === bt.id && r.status === 'pending'
              );
              return (
                <div key={bt.id} className="card p-5">
                  <div className="flex items-start justify-between mb-2 gap-2">
                    <div className="min-w-0">
                      <h3 className="font-semibold text-zinc-900 truncate dark:text-white">{bt.name}</h3>
                      <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1.5 dark:text-zinc-500">
                        <Users className="w-3 h-3" />
                        <span className="font-mono tabular-nums">{bt.member_count}/{MAX_TEAM_SIZE}</span>{' '}
                        {t('teams.memberCountSuffix')}
                      </p>
                    </div>
                    {bt.is_member && (
                      <span className="badge bg-accent-500/10 text-accent-700 border border-accent-500/30 flex-shrink-0 dark:bg-accent-500/15 dark:text-accent-300">
                        {t('teams.memberBadge')}
                      </span>
                    )}
                    {!bt.is_member && bt.is_full && (
                      <span className="badge bg-zinc-200 text-zinc-500 border border-zinc-300 flex-shrink-0 dark:bg-zinc-700/50 dark:text-zinc-400 dark:border-zinc-600/30">
                        {t('teams.fullBadge')}
                      </span>
                    )}
                  </div>

                  <div className="mt-4">
                    {bt.is_member ? (
                      <p className="text-xs text-zinc-500 dark:text-zinc-500">{t('teams.inThisTeam')}</p>
                    ) : bt.has_pending_request ? (
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-amber-600 flex items-center gap-1.5 dark:text-amber-300">
                          <Clock className="w-3.5 h-3.5" />
                          {t('teams.requestPending')}
                        </span>
                        {outgoingForThis && (
                          <button
                            onClick={() => handleCancel(outgoingForThis)}
                            disabled={pendingAction === `cancel-${outgoingForThis.id}`}
                            className="text-xs text-zinc-500 hover:text-red-500 transition-colors disabled:opacity-50 dark:text-zinc-400 dark:hover:text-red-400"
                          >
                            {t('teams.cancelAction')}
                          </button>
                        )}
                      </div>
                    ) : alreadyInTeam ? (
                      <p className="text-xs text-zinc-400 dark:text-zinc-600">
                        {t('teams.leaveFirst')}
                      </p>
                    ) : bt.is_full ? (
                      <p className="text-xs text-zinc-500 dark:text-zinc-500">{t('teams.teamIsFull')}</p>
                    ) : (
                      <button
                        onClick={() => openRequest(bt)}
                        className="w-full text-sm font-medium px-3 py-2 rounded-lg bg-accent-600/10 hover:bg-accent-600/20 border border-accent-500/30 text-accent-700 transition-colors flex items-center justify-center gap-2 dark:bg-accent-600/20 dark:hover:bg-accent-600/30 dark:text-accent-300"
                      >
                        <Send className="w-3.5 h-3.5" />
                        {t('teams.requestToJoin')}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {outgoing.filter((r) => r.status !== 'pending').length > 0 && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-3">{t('teams.historyHeading')}</h2>
          <div className="space-y-1.5">
            {outgoing
              .filter((r) => r.status !== 'pending')
              .slice(0, 10)
              .map((req) => (
                <div
                  key={req.id}
                  className="flex items-center gap-3 text-xs text-zinc-500 px-3 py-1.5 rounded-md bg-zinc-50 border border-zinc-200 dark:bg-zinc-900/30 dark:border-zinc-800/40 dark:text-zinc-500"
                >
                  {req.status === 'accepted' ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 dark:text-emerald-400" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 dark:text-red-400" />
                  )}
                  <span className="text-zinc-800 dark:text-zinc-300">{req.team_name}</span>
                  <span className="text-zinc-400 dark:text-zinc-600">
                    {req.status === 'accepted' ? t('teams.statusAccepted') : t('teams.statusRejected')}
                  </span>
                  <span className="ml-auto text-zinc-400 dark:text-zinc-700">
                    {req.decided_at
                      ? new Date(req.decided_at).toLocaleDateString()
                      : new Date(req.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
