import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ScrollText, RefreshCw } from 'lucide-react';
import { getAuditLog } from '../../api';

// Self-contained audit log viewer: keeps the filter form + the rows
// list local. Mounts once when the user picks the "audit" tab and
// refetches on demand (no automatic polling — the log doesn't change
// frequently enough to warrant it).
export default function AuditLogTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState({ action: '', actor: '', target_type: '' });

  const load = () => {
    const params = {};
    if (filter.action.trim()) params.action = filter.action.trim();
    if (filter.actor.trim()) params.actor = filter.actor.trim();
    if (filter.target_type.trim()) params.target_type = filter.target_type.trim();
    getAuditLog(params).then((r) => setRows(r.data)).catch(() => {});
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex flex-wrap items-center gap-3 dark:border-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2 dark:text-gray-300">
          <ScrollText className="w-4 h-4 text-violet-500 dark:text-violet-400" />
          {t('admin.audit.title')}
          <span className="text-xs font-normal text-slate-400 dark:text-gray-500">({rows.length})</span>
        </h3>
        <div className="flex flex-wrap gap-2 ml-auto items-center">
          <input
            type="text"
            placeholder={t('admin.audit.filterAction')}
            value={filter.action}
            onChange={(e) => setFilter({ ...filter, action: e.target.value })}
            className="input-field text-xs py-1.5 px-2 w-36"
          />
          <input
            type="text"
            placeholder={t('admin.audit.filterActor')}
            value={filter.actor}
            onChange={(e) => setFilter({ ...filter, actor: e.target.value })}
            className="input-field text-xs py-1.5 px-2 w-36"
          />
          <input
            type="text"
            placeholder={t('admin.audit.filterTarget')}
            value={filter.target_type}
            onChange={(e) => setFilter({ ...filter, target_type: e.target.value })}
            className="input-field text-xs py-1.5 px-2 w-36"
          />
          <button onClick={load} className="btn-primary text-xs py-1.5 px-3">
            {t('common.search')}
          </button>
          <button onClick={load} className="btn-secondary text-xs py-1.5 px-3" title={t('common.refresh')}>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-10 dark:text-gray-500">
          {t('admin.audit.empty')}
        </p>
      ) : (
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white/95 backdrop-blur-sm dark:bg-slate-900/95">
              <tr>
                <th className="text-left text-slate-500 font-semibold py-2.5 px-4 dark:text-gray-400">{t('admin.audit.colDate')}</th>
                <th className="text-left text-slate-500 font-semibold py-2.5 px-4 dark:text-gray-400">{t('admin.audit.colActor')}</th>
                <th className="text-left text-slate-500 font-semibold py-2.5 px-4 dark:text-gray-400">{t('admin.audit.colAction')}</th>
                <th className="text-left text-slate-500 font-semibold py-2.5 px-4 dark:text-gray-400">{t('admin.audit.colTarget')}</th>
                <th className="text-left text-slate-500 font-semibold py-2.5 px-4 dark:text-gray-400">{t('admin.audit.colDetail')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50 dark:border-slate-800/30 dark:hover:bg-slate-800/20">
                  <td className="py-2 px-4 text-xs text-slate-500 whitespace-nowrap dark:text-gray-400">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 px-4 text-slate-800 dark:text-gray-200">{row.actor_username || '—'}</td>
                  <td className="py-2 px-4 font-mono text-xs text-violet-700 dark:text-violet-300">{row.action}</td>
                  <td className="py-2 px-4 text-xs text-slate-500 dark:text-gray-400">
                    {row.target_type}
                    {row.target_id != null ? `#${row.target_id}` : ''}
                  </td>
                  <td className="py-2 px-4 text-xs text-slate-500 font-mono break-all dark:text-gray-500">
                    {row.detail}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
