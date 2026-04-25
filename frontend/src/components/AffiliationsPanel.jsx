// Admin CRUD for affiliations (schools / universities / rooms). Tiny
// table editor — the list is expected to be short (dozens, not
// thousands), so no pagination or search.
import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit, Save, X, Building2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import {
  listAffiliations, createAffiliation, updateAffiliation, deleteAffiliation,
} from '../api';
import { useConfirm } from './Confirm';

const BLANK = { name: '', short_name: '', country_code: '', logo_url: '' };

export default function AffiliationsPanel() {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);  // id | 'new' | null
  const [draft, setDraft] = useState(null);

  const refresh = () => {
    setLoading(true);
    listAffiliations()
      .then((r) => setRows(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const startEdit = (a) => {
    setDraft({
      name: a.name || '',
      short_name: a.short_name || '',
      country_code: a.country_code || '',
      logo_url: a.logo_url || '',
    });
    setEditingId(a.id);
  };
  const startCreate = () => {
    setDraft({ ...BLANK });
    setEditingId('new');
  };
  const cancel = () => { setDraft(null); setEditingId(null); };

  const save = async () => {
    try {
      const payload = {
        name: draft.name.trim(),
        short_name: draft.short_name.trim() || null,
        country_code: (draft.country_code || '').trim().toUpperCase().slice(0, 3) || null,
        logo_url: draft.logo_url.trim() || null,
      };
      if (!payload.name) {
        toast.error(t('affiliations.nameRequired'));
        return;
      }
      if (editingId === 'new') await createAffiliation(payload);
      else await updateAffiliation(editingId, payload);
      toast.success(t('common.saved'));
      cancel();
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const remove = async (a) => {
    const ok = await confirm({
      message: t('affiliations.confirmDelete', { name: a.name }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteAffiliation(a.id);
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
          <Building2 className="w-5 h-5 text-violet-500 dark:text-violet-400" />
          {t('affiliations.heading')}
          <span className="text-xs font-normal text-slate-400 dark:text-gray-500">({rows.length})</span>
        </h2>
        <button
          type="button"
          onClick={startCreate}
          className="btn-primary text-xs py-1.5 px-3 inline-flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> {t('affiliations.add')}
        </button>
      </div>

      {editingId !== null && (
        <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">
                {t('affiliations.name')}
              </label>
              <input
                className="input-field text-sm py-1 px-2" value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">
                {t('affiliations.shortName')}
              </label>
              <input
                className="input-field text-sm py-1 px-2" value={draft.short_name}
                onChange={(e) => setDraft({ ...draft, short_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">
                {t('affiliations.country')}
              </label>
              <input
                className="input-field text-sm py-1 px-2 font-mono" value={draft.country_code}
                placeholder="BEL"
                onChange={(e) => setDraft({ ...draft, country_code: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">
                {t('affiliations.logoUrl')}
              </label>
              <input
                className="input-field text-sm py-1 px-2" value={draft.logo_url}
                onChange={(e) => setDraft({ ...draft, logo_url: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={save} className="btn-primary text-xs py-1 px-3">
              <Save className="w-3.5 h-3.5 mr-1 inline" />
              {editingId === 'new' ? t('common.create') : t('common.save')}
            </button>
            <button type="button" onClick={cancel} className="btn-secondary text-xs py-1 px-3">
              <X className="w-3.5 h-3.5 mr-1 inline" /> {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-400 dark:text-gray-500">{t('common.loading')}</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-slate-400 dark:text-gray-500">{t('affiliations.empty')}</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 dark:text-gray-400">
              <th className="text-left py-2 px-3">{t('affiliations.name')}</th>
              <th className="text-left py-2 px-3">{t('affiliations.shortName')}</th>
              <th className="text-left py-2 px-3">{t('affiliations.country')}</th>
              <th className="text-right py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-t border-slate-200/60 dark:border-slate-700/60">
                <td className="py-2 px-3 text-slate-800 dark:text-gray-100">{a.name}</td>
                <td className="py-2 px-3 text-slate-600 font-mono text-xs dark:text-gray-300">{a.short_name || '—'}</td>
                <td className="py-2 px-3 text-slate-600 font-mono text-xs dark:text-gray-300">{a.country_code || '—'}</td>
                <td className="py-2 px-3 text-right">
                  <button
                    type="button" onClick={() => startEdit(a)}
                    className="btn-secondary text-xs py-1 px-2 mr-2"
                  >
                    <Edit className="w-3.5 h-3.5 mr-1 inline" /> {t('common.edit')}
                  </button>
                  <button
                    type="button" onClick={() => remove(a)}
                    className="btn-danger text-xs py-1 px-2"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1 inline" /> {t('common.delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
