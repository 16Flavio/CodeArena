// User-facing: pick (or clear) their solo-entry affiliation from the
// list of admin-curated affiliations. The badge shows up next to their
// username on the ICPC scoreboard when they participate solo.
import { useEffect, useState } from 'react';
import { X, Building2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { listAffiliations, setMySoloAffiliation, getMe } from '../api';
import { useAuth } from '../AuthContext';
import { getToken, tokenIsPersistent } from '../utils/tokenStore';

export default function ChangeAffiliationModal({ onClose }) {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(user?.solo_affiliation_id || '');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listAffiliations()
      .then((r) => setRows(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await setMySoloAffiliation(selected ? Number(selected) : null);
      // Refresh the cached user so the UI knows the new id.
      try {
        const { data: me } = await getMe();
        const token = getToken();
        if (token) login(token, me, { remember: tokenIsPersistent() });
      } catch { /* non-fatal — modal still closes */ }
      toast.success(t('accountModal.toastAffiliationSaved'));
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('accountModal.toastFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md animate-slide-up" role="dialog" aria-modal="true">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            <Building2 className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('accountModal.affiliationTitle')}
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
              {t('accountModal.affiliationField')}
            </label>
            {loading ? (
              <p className="text-sm text-slate-400 dark:text-gray-500">{t('common.loading')}</p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-gray-500">
                {t('accountModal.affiliationEmpty')}
              </p>
            ) : (
              <select
                className="input-field"
                value={selected ?? ''}
                onChange={(e) => setSelected(e.target.value)}
              >
                <option value="">{t('accountModal.affiliationNone')}</option>
                {rows.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}{a.short_name ? ` (${a.short_name})` : ''}
                  </option>
                ))}
              </select>
            )}
            <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
              {t('accountModal.affiliationHint')}
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
