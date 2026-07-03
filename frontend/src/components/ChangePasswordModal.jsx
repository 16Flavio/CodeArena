import { useState } from 'react';
import { X, Eye, EyeOff, KeyRound } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { changePassword } from '../api';
import { setToken, tokenIsPersistent } from '../utils/tokenStore';
import { extractErrorMessage } from '../utils/apiError';

export default function ChangePasswordModal({ onClose }) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.new_password !== form.confirm) {
      toast.error(t('accountModal.toastMismatch'));
      return;
    }
    if (form.new_password.length < 4) {
      toast.error(t('accountModal.toastTooShort'));
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
      });
      // The backend revokes every outstanding session (token_version
      // bump) and hands back a fresh token so THIS session survives.
      if (data?.access_token) setToken(data.access_token, { remember: tokenIsPersistent() });
      toast.success(t('accountModal.toastPasswordUpdated'));
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
            <KeyRound className="w-5 h-5 text-accent-500 dark:text-accent-400" />
            {t('accountModal.passwordTitle')}
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
              {t('accountModal.currentPassword')}
            </label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input-field pr-12"
                value={form.current_password}
                onChange={(e) => setForm({ ...form, current_password: e.target.value })}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 transition-colors dark:text-zinc-500 dark:hover:text-zinc-300"
                aria-label={showPw ? t('accountModal.hide') : t('accountModal.show')}
              >
                {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('accountModal.newPassword')}
            </label>
            <input
              type={showPw ? 'text' : 'password'}
              className="input-field"
              placeholder={t('accountModal.minCharsHint')}
              value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })}
              autoComplete="new-password"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
              {t('accountModal.confirmPassword')}
            </label>
            <input
              type="password"
              className="input-field"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              autoComplete="new-password"
              required
            />
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
