import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Shield, ShieldOff, Trash2, KeyRound, UserCog } from 'lucide-react';
import { toggleAdmin, toggleOrganizer, deleteUser, adminDisableTotp } from '../../api';
import { useConfirm } from '../Confirm';
import { extractErrorMessage } from '../../utils/apiError';

// Pure rendering + local action handlers. State (the user list) stays
// in Admin.jsx because the contest editor's allowlist picker reuses it.
// The parent passes ``onChange`` so we can ask for a refresh after a
// row mutation.
export default function UsersTab({ users, currentUser, onChange }) {
  const { t } = useTranslation();
  const confirm = useConfirm();

  const handleToggleAdmin = async (id) => {
    try {
      await toggleAdmin(id);
      toast.success(t('admin.users.toastStatus'));
      onChange?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const handleToggleOrganizer = async (id) => {
    try {
      await toggleOrganizer(id);
      toast.success(t('admin.users.toastStatus'));
      onChange?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const handleDelete = async (id, username) => {
    const ok = await confirm({
      message: t('admin.users.confirmDelete', { user: username }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteUser(id);
      toast.success(t('admin.users.toastDeleted'));
      onChange?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const handleResetTotp = async (id, username) => {
    const ok = await confirm({
      title: t('admin.users.resetTotpTitle'),
      message: t('admin.users.confirmResetTotp', { user: username }),
      danger: true,
    });
    if (!ok) return;
    try {
      await adminDisableTotp(id);
      toast.success(t('admin.users.toastTotpReset'));
      onChange?.();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100/60 dark:bg-slate-800/50">
              <th className="text-left text-slate-500 font-semibold py-4 px-5 dark:text-gray-400">{t('admin.users.colUser')}</th>
              <th className="text-left text-slate-500 font-semibold py-4 px-5 dark:text-gray-400">{t('admin.users.colEmail')}</th>
              <th className="text-left text-slate-500 font-semibold py-4 px-5 dark:text-gray-400">{t('admin.users.colRole')}</th>
              <th className="text-left text-slate-500 font-semibold py-4 px-5 dark:text-gray-400">{t('admin.users.colJoined')}</th>
              <th className="text-right text-slate-500 font-semibold py-4 px-5 dark:text-gray-400">{t('admin.users.colActions')}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50 dark:border-slate-800/30 dark:hover:bg-slate-800/20">
                <td className="py-3 px-5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500/30 to-indigo-500/30 flex items-center justify-center text-sm font-bold text-violet-700 dark:text-violet-300">
                      {u.username[0].toUpperCase()}
                    </div>
                    <span className="text-slate-900 font-medium dark:text-white">{u.username}</span>
                  </div>
                </td>
                <td className="py-3 px-5 text-slate-500 dark:text-gray-400">{u.email}</td>
                <td className="py-3 px-5">
                  {u.is_admin ? (
                    <span className="badge-admin">{t('admin.users.roleAdmin')}</span>
                  ) : u.is_organizer ? (
                    <span className="badge-admin" title={t('admin.users.roleOrganizerHint')}>
                      {t('admin.users.roleOrganizer')}
                    </span>
                  ) : (
                    <span className="badge-inactive">{t('admin.users.roleUser')}</span>
                  )}
                </td>
                <td className="py-3 px-5 text-slate-400 text-xs dark:text-gray-500">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="py-3 px-5 text-right">
                  {u.id !== currentUser.id && (
                    <div className="flex items-center justify-end gap-2">
                      {u.totp_enabled && (
                        <button
                          onClick={() => handleResetTotp(u.id, u.username)}
                          className="p-2 rounded-lg hover:bg-orange-500/10 text-orange-500 hover:text-orange-600 transition-colors dark:text-orange-400 dark:hover:text-orange-300"
                          title={t('admin.users.resetTotpTitle')}
                        >
                          <KeyRound className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleToggleAdmin(u.id)}
                        className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-amber-500 transition-colors dark:hover:bg-slate-700/50 dark:text-gray-400 dark:hover:text-amber-400"
                        title={u.is_admin ? t('admin.users.removeAdmin') : t('admin.users.makeAdmin')}
                      >
                        {u.is_admin ? <ShieldOff className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                      </button>
                      {!u.is_admin && (
                        <button
                          onClick={() => handleToggleOrganizer(u.id)}
                          className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-violet-500 transition-colors dark:hover:bg-slate-700/50 dark:text-gray-400 dark:hover:text-violet-400"
                          title={u.is_organizer ? t('admin.users.removeOrganizer') : t('admin.users.makeOrganizer')}
                        >
                          <UserCog className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(u.id, u.username)}
                        className="p-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors dark:text-gray-400 dark:hover:text-red-400"
                        title={t('admin.users.deleteUser')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
