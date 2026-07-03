import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Trophy, Plus, Trash2, Edit, X, Upload, FileText, Code, Target, Eye,
  FlaskConical, Copy, Pause, Play,
} from 'lucide-react';
import {
  getContest, updateContest, deleteContest,
  createInstance, deleteInstance, duplicateContest,
} from '../../api';
import ContestFormModal from './ContestFormModal';
import EditInstanceModal from './EditInstanceModal';
import { useConfirm } from '../Confirm';
import { toUtcIso, formatDateTime } from '../../utils/datetime';
import { extractErrorMessage } from '../../utils/apiError';

// Contest list + creation/edit orchestration. The heavy form lives in
// ContestFormModal; this component owns which contest is being edited
// and the per-contest instance management. ``users`` is threaded down
// to the form's allowlist picker; ``onChange`` asks Admin.jsx to
// reload the contest list.
export default function ContestsTab({ contests, users, onChange }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  // Full contest being edited (null = create mode) — fetched fresh
  // before the form opens so instances/scripts are current.
  const [editContest, setEditContest] = useState(null);
  const [showForm, setShowForm] = useState(false);
  // Step 1 of contest creation — admin picks "output scoring" vs "ICPC"
  // before any form shows up. Cleaner than hiding a dropdown in the middle
  // of the long form.
  const [showKindPicker, setShowKindPicker] = useState(false);
  const [createKind, setCreateKind] = useState('output');
  const [instanceFile, setInstanceFile] = useState(null);
  const [instanceForm, setInstanceForm] = useState({
    name: '',
    unlock_delay_minutes: 0,
    unlock_at_absolute: '',
    unlock_mode: 'relative', // 'relative' | 'absolute'
  });
  // Instance currently being edited (full row) — opens the edit modal.
  const [editingInstance, setEditingInstance] = useState(null);

  const startEdit = async (contest) => {
    try {
      const { data: full } = await getContest(contest.id);
      setEditContest(full);
      setShowForm(true);
    } catch {
      toast.error(t('admin.contests.toastLoadDetailsFailed'));
    }
  };

  const handleDeleteContest = async (id, title) => {
    const ok = await confirm({
      message: t('admin.contests.confirmDelete', { title }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteContest(id);
      toast.success(t('admin.contests.toastDeleted'));
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.contests.toastFailed')));
    }
  };

  const handleAddInstance = async (contestId) => {
    if (!instanceFile || !instanceForm.name) {
      toast.error(t('admin.contests.toastNeedFields'));
      return;
    }
    try {
      const fd = new FormData();
      fd.append('name', instanceForm.name);
      if (instanceForm.unlock_mode === 'absolute' && instanceForm.unlock_at_absolute) {
        fd.append('unlock_delay_seconds', '0');
        fd.append('unlock_at_absolute', toUtcIso(instanceForm.unlock_at_absolute) || '');
      } else {
        const delay = Math.max(0, Math.floor(Number(instanceForm.unlock_delay_minutes) || 0) * 60);
        fd.append('unlock_delay_seconds', String(delay));
      }
      fd.append('file', instanceFile);
      await createInstance(contestId, fd);
      toast.success(t('admin.instance.toastAdded'));
      setInstanceFile(null);
      setInstanceForm({ name: '', unlock_delay_minutes: 0, unlock_at_absolute: '', unlock_mode: 'relative' });
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const handleDeleteInstance = async (id) => {
    const ok = await confirm({
      message: t('admin.instance.confirmDelete'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteInstance(id);
      toast.success(t('admin.instance.toastDeleted'));
      onChange();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => {
          setEditContest(null);
          setShowKindPicker(true);
        }}
        className="btn-primary"
      >
        <Plus className="w-4 h-4 mr-2 inline" />
        {t('admin.contests.new')}
      </button>

      {showKindPicker && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowKindPicker(false)}
        >
          <div
            className="card p-6 w-full max-w-2xl animate-fade-in"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-white">
                {t('admin.kindPicker.title')}
              </h2>
              <button
                onClick={() => setShowKindPicker(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
                aria-label={t('accountModal.close')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-zinc-500 mb-6 dark:text-zinc-400">
              {t('admin.kindPicker.subtitle')}
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => {
                  setCreateKind('output');
                  setShowKindPicker(false);
                  setShowForm(true);
                }}
                className="text-left p-5 rounded-lg border-2 border-zinc-200 hover:border-accent-500 hover:bg-accent-500/5 transition-colors dark:border-zinc-700 dark:hover:border-accent-400"
              >
                <div className="flex items-center gap-2 mb-2">
                  <FlaskConical className="w-5 h-5 text-accent-500 dark:text-accent-400" />
                  <h3 className="font-semibold text-zinc-900 dark:text-white">
                    {t('admin.kindPicker.outputTitle')}
                  </h3>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {t('admin.kindPicker.outputBody')}
                </p>
                <p className="text-[11px] text-zinc-400 mt-2 dark:text-zinc-500">
                  {t('admin.kindPicker.outputExample')}
                </p>
              </button>
              <button
                type="button"
                onClick={() => {
                  setCreateKind('icpc');
                  setShowKindPicker(false);
                  setShowForm(true);
                }}
                className="text-left p-5 rounded-lg border-2 border-zinc-200 hover:border-accent-500 hover:bg-accent-500/5 transition-colors dark:border-zinc-700 dark:hover:border-accent-400"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Code className="w-5 h-5 text-accent-500 dark:text-accent-400" />
                  <h3 className="font-semibold text-zinc-900 dark:text-white">
                    {t('admin.kindPicker.icpcTitle')}
                  </h3>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {t('admin.kindPicker.icpcBody')}
                </p>
                <p className="text-[11px] text-zinc-400 mt-2 dark:text-zinc-500">
                  {t('admin.kindPicker.icpcExample')}
                </p>
              </button>
            </div>
          </div>
        </div>
      )}

      {showForm && (
        <ContestFormModal
          contest={editContest}
          initialKind={createKind}
          users={users}
          onClose={() => {
            setShowForm(false);
            setEditContest(null);
          }}
          onChange={onChange}
        />
      )}

      {contests.length === 0 ? (
        <div className="card p-12 text-center">
          <Trophy className="w-14 h-14 text-zinc-300 mx-auto mb-4 dark:text-zinc-600" />
          <h3 className="text-xl font-bold text-zinc-900 mb-2 dark:text-white">{t('admin.contests.noneHeading')}</h3>
          <p className="text-zinc-500 dark:text-zinc-400">{t('admin.contests.noneBody')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {contests.map((c) => (
            <div key={c.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="text-lg font-bold text-zinc-900 dark:text-white">{c.title}</h3>
                    <span className={c.is_active ? 'badge-active' : 'badge-inactive'}>
                      {c.is_active ? t('admin.contests.active') : t('admin.contests.inactive')}
                    </span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                      c.kind === 'icpc'
                        ? 'bg-sky-500/15 text-sky-700 border-sky-500/30 dark:text-sky-300'
                        : 'bg-accent-500/15 text-accent-700 border-accent-500/30 dark:text-accent-300'
                    }`}>
                      {c.kind === 'icpc'
                        ? <><Code className="w-3 h-3" /> ICPC</>
                        : <><FlaskConical className="w-3 h-3" /> {t('admin.form.kindOutput').split(' ')[0]}</>
                      }
                    </span>
                  </div>
                  <p className="text-zinc-500 text-sm dark:text-zinc-400">{c.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/scoreboard/${c.id}`}
                    className="p-2 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-accent-500 transition-colors dark:hover:bg-zinc-700/50 dark:text-zinc-400 dark:hover:text-accent-400"
                    title={t('admin.contests.viewBoard')}
                  >
                    <Eye className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={async () => {
                      try {
                        await updateContest(c.id, { is_active: !c.is_active });
                        toast.success(c.is_active ? t('admin.contests.toastPaused') : t('admin.contests.toastResumed'));
                        onChange();
                      } catch (err) {
                        toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
                      }
                    }}
                    className={`p-2 rounded-lg transition-colors ${
                      c.is_active
                        ? 'hover:bg-amber-500/10 text-zinc-400 hover:text-amber-500 dark:text-zinc-400 dark:hover:text-amber-400'
                        : 'hover:bg-emerald-500/10 text-zinc-400 hover:text-emerald-500 dark:text-zinc-400 dark:hover:text-emerald-400'
                    }`}
                    title={c.is_active ? t('admin.contests.pause') : t('admin.contests.resume')}
                  >
                    {c.is_active
                      ? <Pause className="w-4 h-4" />
                      : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => startEdit(c)}
                    className="p-2 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-accent-500 transition-colors dark:hover:bg-zinc-700/50 dark:text-zinc-400 dark:hover:text-accent-400"
                    title={t('admin.contests.edit')}
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        await duplicateContest(c.id);
                        toast.success(t('admin.contests.duplicated'));
                        onChange();
                      } catch (err) {
                        toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
                      }
                    }}
                    className="p-2 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-accent-500 transition-colors dark:hover:bg-zinc-700/50 dark:text-zinc-400 dark:hover:text-accent-400"
                    title={t('admin.contests.duplicate')}
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteContest(c.id, c.title)}
                    className="p-2 rounded-lg hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-400 dark:hover:text-red-400"
                    title={t('admin.contests.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {c.kind === 'icpc' ? (
                <div className="bg-zinc-50 rounded-lg p-4 text-sm text-zinc-500 dark:bg-zinc-800/30 dark:text-zinc-400">
                  {t('admin.contests.icpcEditHint')}
                </div>
              ) : (
              <div className="bg-zinc-50 rounded-lg p-4 dark:bg-zinc-800/30">
                <h4 className="text-sm font-semibold text-zinc-700 mb-3 flex items-center gap-2 dark:text-zinc-300">
                  <Target className="w-4 h-4 text-accent-500 dark:text-accent-400" />
                  {t('admin.contests.instancesHeading', { count: c.instances?.length || 0 })}
                </h4>

                {c.instances?.length > 0 && (
                  <div className="space-y-2 mb-3">
                    {c.instances.map((inst) => (
                      <div
                        key={inst.id}
                        className="flex items-center justify-between py-2 px-3 rounded-lg bg-white border border-zinc-200 dark:bg-zinc-700/20 dark:border-transparent"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="w-4 h-4 text-accent-500 flex-shrink-0 dark:text-accent-400" />
                          <span className="text-sm text-zinc-700 truncate dark:text-zinc-200">{inst.name}</span>
                          {inst.unlock_delay_seconds > 0 && (
                            <span
                              className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-400"
                              title={inst.unlock_at ? t('admin.instance.unlocksAt', { at: formatDateTime(inst.unlock_at) }) : undefined}
                            >
                              +{Math.round(inst.unlock_delay_seconds / 60)} min
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => setEditingInstance(inst)}
                            className="p-1 rounded hover:bg-accent-500/10 text-zinc-400 hover:text-accent-500 transition-colors dark:text-zinc-500 dark:hover:text-accent-400"
                            title={t('admin.contests.editInstance')}
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteInstance(inst.id)}
                            className="p-1 rounded hover:bg-red-500/10 text-zinc-400 hover:text-red-500 transition-colors dark:text-zinc-500 dark:hover:text-red-400"
                            title={t('admin.contests.deleteInstance')}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[150px]">
                    <input
                      type="text"
                      className="input-field text-sm py-2"
                      placeholder={t('admin.contests.instanceNamePlaceholder')}
                      value={instanceForm.name}
                      onChange={(e) => setInstanceForm({ ...instanceForm, name: e.target.value })}
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="w-28">
                      <select
                        className="input-field text-sm py-2"
                        value={instanceForm.unlock_mode}
                        onChange={(e) =>
                          setInstanceForm({ ...instanceForm, unlock_mode: e.target.value })
                        }
                        title={t('admin.instance.unlockModeHint')}
                      >
                        <option value="relative">{t('admin.instance.unlockRelative')}</option>
                        <option value="absolute">{t('admin.instance.unlockAbsolute')}</option>
                      </select>
                    </div>
                    {instanceForm.unlock_mode === 'absolute' ? (
                      <div className="w-48">
                        <input
                          type="datetime-local"
                          className="input-field text-sm py-2"
                          value={instanceForm.unlock_at_absolute}
                          onChange={(e) =>
                            setInstanceForm({ ...instanceForm, unlock_at_absolute: e.target.value })
                          }
                          title={t('admin.instance.unlockAbsoluteHint')}
                        />
                      </div>
                    ) : (
                      <div className="w-28">
                        <input
                          type="number"
                          min={0}
                          step={1}
                          className="input-field text-sm py-2"
                          placeholder={t('admin.contests.unlockDelayPlaceholder')}
                          value={instanceForm.unlock_delay_minutes}
                          onChange={(e) =>
                            setInstanceForm({ ...instanceForm, unlock_delay_minutes: e.target.value })
                          }
                          title={t('admin.contests.unlockDelayTitle')}
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-[150px]">
                    <input
                      type="file"
                      onChange={(e) => setInstanceFile(e.target.files[0])}
                      className="input-field text-sm py-2 file:mr-2 file:py-0.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-accent-600 file:text-white"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddInstance(c.id)}
                    className="btn-primary text-sm py-2"
                  >
                    <Upload className="w-4 h-4 mr-1 inline" />
                    {t('admin.contests.addInstance')}
                  </button>
                </div>

                {(!c.instances || c.instances.length === 0) && (
                  <p className="text-zinc-400 text-sm text-center py-2 mt-2 dark:text-zinc-600">
                    {t('admin.contests.noInstancesYet')}
                  </p>
                )}
              </div>
              )}
            </div>
          ))}
        </div>
      )}

      {editingInstance && (
        <EditInstanceModal
          instance={editingInstance}
          onClose={() => setEditingInstance(null)}
          onSaved={() => { setEditingInstance(null); onChange(); }}
        />
      )}
    </div>
  );
}
