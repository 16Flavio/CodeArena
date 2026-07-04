import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Medal, Plus, Trash2, Eye, EyeOff, Save, X, Code, FlaskConical,
} from 'lucide-react';
import {
  listLeagues, createLeague, updateLeague, deleteLeague,
  addLeagueEvent, updateLeagueEvent, removeLeagueEvent,
} from '../../api';
import { useConfirm } from '../Confirm';
import { extractErrorMessage } from '../../utils/apiError';

// League CRUD + event attachment. ``contests`` comes from Admin.jsx
// (already loaded there for the other tabs) and feeds the "add event"
// contest picker; leagues themselves are fetched here.
export default function LeaguesTab({ contests }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', season: '', description: '' });
  // Per-league "add event" drafts and per-event coefficient drafts,
  // keyed by league/event id so several cards can be edited at once.
  const [addForms, setAddForms] = useState({});   // leagueId -> { contest_id, coefficient }
  const [coefDrafts, setCoefDrafts] = useState({}); // eventId -> string

  const refresh = async () => {
    try {
      const r = await listLeagues();
      setLeagues(r.data || []);
    } catch {
      toast.error(t('admin.leagues.toastLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Event endpoints return the updated LeagueOut — patch it in place
  // instead of refetching the whole list.
  const patchLeague = (updated) =>
    setLeagues((ls) => ls.map((l) => (l.id === updated.id ? updated : l)));

  const handleCreate = async () => {
    if (!createForm.name.trim()) {
      toast.error(t('admin.leagues.toastNeedName'));
      return;
    }
    try {
      await createLeague({
        name: createForm.name.trim(),
        season: createForm.season.trim(),
        description: createForm.description.trim(),
      });
      toast.success(t('admin.leagues.toastCreated'));
      setCreateForm({ name: '', season: '', description: '' });
      setShowCreate(false);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  const handleTogglePublish = async (league) => {
    try {
      await updateLeague(league.id, { is_published: !league.is_published });
      toast.success(league.is_published
        ? t('admin.leagues.toastUnpublished')
        : t('admin.leagues.toastPublished'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  const handleDelete = async (league) => {
    const ok = await confirm({
      message: t('admin.leagues.confirmDelete', { name: league.name }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteLeague(league.id);
      toast.success(t('admin.leagues.toastDeleted'));
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  const handleAddEvent = async (league) => {
    const form = addForms[league.id] || {};
    if (!form.contest_id) {
      toast.error(t('admin.leagues.toastNeedContest'));
      return;
    }
    try {
      const r = await addLeagueEvent(league.id, {
        contest_id: Number(form.contest_id),
        coefficient: Number(form.coefficient) || 1,
      });
      patchLeague(r.data);
      setAddForms((f) => ({ ...f, [league.id]: { contest_id: '', coefficient: '1' } }));
      toast.success(t('admin.leagues.toastEventAdded'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  const handleSaveCoef = async (league, ev) => {
    const draft = coefDrafts[ev.id];
    const value = Number(draft);
    if (!Number.isFinite(value) || value <= 0) {
      toast.error(t('admin.leagues.toastBadCoefficient'));
      return;
    }
    try {
      const r = await updateLeagueEvent(league.id, ev.id, { coefficient: value });
      patchLeague(r.data);
      setCoefDrafts((d) => { const n = { ...d }; delete n[ev.id]; return n; });
      toast.success(t('admin.leagues.toastEventUpdated'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  const handleRemoveEvent = async (league, ev) => {
    try {
      const r = await removeLeagueEvent(league.id, ev.id);
      patchLeague(r.data);
      toast.success(t('admin.leagues.toastEventRemoved'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.leagues.toastFailed')));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button onClick={() => setShowCreate((v) => !v)} className="btn-primary">
        <Plus className="w-4 h-4 mr-2 inline" />
        {t('admin.leagues.new')}
      </button>

      {showCreate && (
        <div className="card p-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-white">
              {t('admin.leagues.new')}
            </h3>
            <button
              onClick={() => setShowCreate(false)}
              className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:hover:text-white"
              aria-label={t('common.close')}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <input
              type="text"
              className="input-field"
              placeholder={t('admin.leagues.namePlaceholder')}
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
            />
            <input
              type="text"
              className="input-field"
              placeholder={t('admin.leagues.seasonPlaceholder')}
              value={createForm.season}
              onChange={(e) => setCreateForm({ ...createForm, season: e.target.value })}
            />
          </div>
          <textarea
            className="input-field"
            rows={2}
            placeholder={t('admin.leagues.descriptionPlaceholder')}
            value={createForm.description}
            onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
          />
          <button onClick={handleCreate} className="btn-primary">
            {t('common.create')}
          </button>
        </div>
      )}

      {leagues.length === 0 ? (
        <div className="card p-12 text-center">
          <Medal className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">
            {t('admin.leagues.noneHeading')}
          </h3>
          <p className="text-zinc-500 dark:text-zinc-400">{t('admin.leagues.noneBody')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {leagues.map((league) => {
            const attachedIds = new Set(league.events.map((e) => e.contest_id));
            const available = contests.filter((c) => !attachedIds.has(c.id));
            const addForm = addForms[league.id] || { contest_id: '', coefficient: '1' };
            return (
              <div key={league.id} className="card p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="text-lg font-bold text-zinc-900 dark:text-white">
                        {league.name}
                      </h3>
                      {league.season && (
                        <span className="badge bg-zinc-100 text-zinc-600 border border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700">
                          {league.season}
                        </span>
                      )}
                      <span className={league.is_published ? 'badge-active' : 'badge-inactive'}>
                        {league.is_published
                          ? t('admin.leagues.published')
                          : t('admin.leagues.draft')}
                      </span>
                    </div>
                    {league.description && (
                      <p className="text-zinc-500 text-sm dark:text-zinc-400">
                        {league.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTogglePublish(league)}
                      className={`p-2 rounded-lg transition-colors ${
                        league.is_published
                          ? 'hover:bg-amber-500/10 text-zinc-400 hover:text-amber-500 dark:text-zinc-400 dark:hover:text-amber-400'
                          : 'hover:bg-emerald-500/10 text-zinc-400 hover:text-emerald-500 dark:text-zinc-400 dark:hover:text-emerald-400'
                      }`}
                      title={league.is_published
                        ? t('admin.leagues.unpublish')
                        : t('admin.leagues.publish')}
                    >
                      {league.is_published
                        ? <EyeOff className="w-4 h-4" />
                        : <Eye className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(league)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-400 dark:hover:text-red-400"
                      title={t('admin.leagues.delete')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="bg-zinc-50 rounded-lg p-4 dark:bg-zinc-800/30">
                  <h4 className="text-sm font-semibold text-zinc-700 mb-3 flex items-center gap-2 dark:text-zinc-300">
                    <Medal className="w-4 h-4 text-accent-500 dark:text-accent-400" />
                    {t('admin.leagues.eventsHeading', { count: league.events.length })}
                  </h4>

                  {league.events.length > 0 && (
                    <div className="space-y-2 mb-3">
                      {league.events.map((ev) => (
                        <div
                          key={ev.id}
                          className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-white border border-zinc-200 dark:bg-zinc-700/20 dark:border-transparent"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            {ev.contest_kind === 'icpc'
                              ? <Code className="w-4 h-4 text-sky-500 shrink-0 dark:text-sky-400" />
                              : <FlaskConical className="w-4 h-4 text-accent-500 shrink-0 dark:text-accent-400" />}
                            <span className="text-sm text-zinc-700 truncate dark:text-zinc-200">
                              {ev.contest_title}
                            </span>
                            <span className={ev.finished ? 'badge-active' : 'badge-inactive'}>
                              {ev.finished
                                ? t('admin.leagues.finished')
                                : t('admin.leagues.upcoming')}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <input
                              type="number"
                              min={0}
                              step={0.1}
                              className="input-field text-sm py-1 w-20 font-mono tabular-nums"
                              value={coefDrafts[ev.id] ?? String(ev.coefficient)}
                              onChange={(e) =>
                                setCoefDrafts((d) => ({ ...d, [ev.id]: e.target.value }))}
                              title={t('admin.leagues.coefficient')}
                            />
                            {coefDrafts[ev.id] != null
                              && coefDrafts[ev.id] !== String(ev.coefficient) && (
                              <button
                                onClick={() => handleSaveCoef(league, ev)}
                                className="p-1 rounded hover:bg-accent-500/10 text-zinc-400 hover:text-accent-500 transition-colors dark:text-zinc-500 dark:hover:text-accent-400"
                                title={t('admin.leagues.saveCoefficient')}
                              >
                                <Save className="w-3.5 h-3.5" />
                              </button>
                            )}
                            <button
                              onClick={() => handleRemoveEvent(league, ev)}
                              className="p-1 rounded hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-500 dark:hover:text-red-400"
                              title={t('admin.leagues.removeEvent')}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {available.length === 0 && league.events.length > 0 ? (
                    <p className="text-zinc-400 text-sm py-1 dark:text-zinc-600">
                      {t('admin.leagues.allAttached')}
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-3 items-end">
                      <div className="flex-1 min-w-[180px]">
                        <select
                          className="input-field text-sm py-2"
                          value={addForm.contest_id}
                          onChange={(e) => setAddForms((f) => ({
                            ...f,
                            [league.id]: { ...addForm, contest_id: e.target.value },
                          }))}
                        >
                          <option value="">{t('admin.leagues.selectContest')}</option>
                          {available.map((c) => (
                            <option key={c.id} value={c.id}>{c.title}</option>
                          ))}
                        </select>
                      </div>
                      <div className="w-28">
                        <input
                          type="number"
                          min={0}
                          step={0.1}
                          className="input-field text-sm py-2 font-mono tabular-nums"
                          value={addForm.coefficient}
                          onChange={(e) => setAddForms((f) => ({
                            ...f,
                            [league.id]: { ...addForm, coefficient: e.target.value },
                          }))}
                          title={t('admin.leagues.coefficient')}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleAddEvent(league)}
                        className="btn-primary text-sm py-2"
                      >
                        <Plus className="w-4 h-4 mr-1 inline" />
                        {t('admin.leagues.addEvent')}
                      </button>
                    </div>
                  )}

                  {league.events.length === 0 && (
                    <p className="text-zinc-400 text-sm text-center py-2 mt-2 dark:text-zinc-600">
                      {t('admin.leagues.noEvents')}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
