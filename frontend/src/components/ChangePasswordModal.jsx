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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md animate-slide-up" role="dialog" aria-modal="true">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            <KeyRound className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('accountModal.passwordTitle')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
            aria-label={t('accountModal.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
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
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors dark:text-gray-500 dark:hover:text-gray-300"
                aria-label={showPw ? t('accountModal.hide') : t('accountModal.show')}
              >
                {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
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
            <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
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
