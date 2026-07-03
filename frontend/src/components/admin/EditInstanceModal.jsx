import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Edit, X } from 'lucide-react';
import { updateInstance } from '../../api';
import { extractErrorMessage } from '../../utils/apiError';

// Inline editor for an Instance row. Only sends the fields that the
// admin actually touched (so an unchanged save is a single 200 with
// no DB write); also lets them replace the input file or clear the
// absolute date overrides explicitly.
//
// Lifted from Admin.jsx so the file stays under reasonable size.
export default function EditInstanceModal({ instance, onClose, onSaved }) {
  const { t } = useTranslation();
  const [name, setName] = useState(instance.name || '');
  const [unlockMinutes, setUnlockMinutes] = useState(
    String(Math.round((instance.unlock_delay_seconds || 0) / 60))
  );
  const [unlockAt, setUnlockAt] = useState(toLocalInput(instance.unlock_at_absolute));
  const [closeAt, setCloseAt] = useState(toLocalInput(instance.close_at_absolute));
  const [replaceFile, setReplaceFile] = useState(null);
  const [saving, setSaving] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error(t('admin.contests.instanceNameRequired'));
      return;
    }
    setSaving(true);
    try {
      const fd = new FormData();
      if (name.trim() !== instance.name) {
        fd.append('name', name.trim());
      }
      const secs = Math.max(0, parseInt(unlockMinutes || '0', 10) || 0) * 60;
      if (secs !== (instance.unlock_delay_seconds || 0)) {
        fd.append('unlock_delay_seconds', String(secs));
      }
      const origUnlock = toLocalInput(instance.unlock_at_absolute);
      if (unlockAt !== origUnlock) {
        fd.append('unlock_at_absolute', localToUtcIso(unlockAt));
      }
      const origClose = toLocalInput(instance.close_at_absolute);
      if (closeAt !== origClose) {
        fd.append('close_at_absolute', localToUtcIso(closeAt));
      }
      if (replaceFile) {
        fd.append('file', replaceFile, replaceFile.name);
      }
      const hasAny = [...fd.keys()].length > 0;
      if (hasAny) {
        await updateInstance(instance.id, fd);
        toast.success(t('admin.contests.instanceUpdated'));
      }
      onSaved();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.contests.toastFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md animate-slide-up" role="dialog" aria-modal="true">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            <Edit className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('admin.contests.editInstance')}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
            aria-label="close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={save} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
              {t('admin.contests.instanceNamePlaceholder')}
            </label>
            <input
              type="text"
              className="input-field text-sm py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
              {t('admin.contests.instanceUnlockMinutes')}
            </label>
            <input
              type="number"
              min={0}
              className="input-field text-sm py-2"
              value={unlockMinutes}
              onChange={(e) => setUnlockMinutes(e.target.value)}
            />
            <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
              {t('admin.contests.instanceUnlockHint')}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
                {t('admin.contests.instanceAvailableFrom')}
              </label>
              <input
                type="datetime-local"
                className="input-field text-sm py-2"
                value={unlockAt}
                onChange={(e) => setUnlockAt(e.target.value)}
              />
              <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
                {t('admin.contests.instanceAvailableFromHint')}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
                {t('admin.contests.instanceAvailableUntil')}
              </label>
              <input
                type="datetime-local"
                className="input-field text-sm py-2"
                value={closeAt}
                onChange={(e) => setCloseAt(e.target.value)}
              />
              <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
                {t('admin.contests.instanceAvailableUntilHint')}
              </p>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
              {t('admin.contests.instanceReplaceFile')}
            </label>
            <input
              type="file"
              className="input-field text-sm py-2 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-violet-600 file:text-white"
              onChange={(e) => setReplaceFile(e.target.files?.[0] || null)}
            />
            <p className="text-[11px] text-amber-600 mt-1 dark:text-amber-400">
              {t('admin.contests.instanceReplaceFileWarn')}
            </p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn-primary text-sm" disabled={saving}>
              {saving ? t('common.sending') : t('common.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function toLocalInput(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return '';
  }
}

function localToUtcIso(v) {
  return v ? new Date(v).toISOString() : '';
}
