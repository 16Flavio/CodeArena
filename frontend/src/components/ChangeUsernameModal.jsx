import { useState } from 'react';
import { X, UserCog } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { changeUsername } from '../api';
import { useAuth } from '../AuthContext';
import { getToken, tokenIsPersistent } from '../utils/tokenStore';
import { extractErrorMessage } from '../utils/apiError';

export default function ChangeUsernameModal({ onClose }) {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const [form, setForm] = useState({ current_password: '', new_username: user?.username || '' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.new_username.trim()) {
      toast.error(t('accountModal.toastUsernameEmpty'));
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await changeUsername({
        current_password: form.current_password,
        new_username: form.new_username.trim(),
      });
      const token = getToken();
      // Keep the "remember me" preference - don't silently demote
      // a persistent login to session-only just because the user
      // changed their username.
      if (token) login(token, data, { remember: tokenIsPersistent() });
      toast.success(t('accountModal.toastUsernameUpdated'));
      onClose();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('accountModal.toastFailed')));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="card p-6 w-full max-w-md animate-fade-in" role="dialog" aria-modal="true">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
            <UserCog className="w-5 h-5 text-accent-500 dark:text-accent-400" />
            {t('accountModal.usernameTitle')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900 transition-colors dark:hover:bg-zinc-800 dark:text-zinc-400 dark:hover:text-white"
            aria-label={t('accountModal.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('accountModal.newUsername')}
            </label>
            <input
              type="text"
              className="input-field"
              value={form.new_username}
              onChange={(e) => setForm({ ...form, new_username: e.target.value })}
              required
              minLength={2}
              maxLength={50}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('accountModal.currentPassword')}
            </label>
            <input
              type="password"
              className="input-field"
              value={form.current_password}
              onChange={(e) => setForm({ ...form, current_password: e.target.value })}
              autoComplete="current-password"
              required
            />
            <p className="text-[11px] text-zinc-400 mt-1 dark:text-zinc-600">
              {t('accountModal.identityHint')}
            </p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn-primary text-sm" disabled={submitting}>
              {submitting ? t('accountModal.saving') : t('accountModal.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
