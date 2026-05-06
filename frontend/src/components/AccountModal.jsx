import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X, KeyRound, UserCog, Building2, ShieldCheck, Eye, EyeOff,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';
import { Link } from 'react-router-dom';
import {
  changePassword, changeUsername, listAffiliations, setMySoloAffiliation,
} from '../api';

// Single, centered, comfortable place to manage account-level settings.
// Replaces the 3 cramped sidebar buttons (password / username /
// affiliation) with one "Mon compte" entry point + tabs. The Security
// tab links out to the dedicated /security page since 2FA setup
// involves a QR scan that wants more room than a modal.

const TABS = [
  { id: 'password', icon: KeyRound, labelKey: 'accountModal.tabPassword' },
  { id: 'username', icon: UserCog, labelKey: 'accountModal.tabUsername' },
  { id: 'affiliation', icon: Building2, labelKey: 'accountModal.tabAffiliation' },
  { id: 'security', icon: ShieldCheck, labelKey: 'accountModal.tabSecurity' },
];

export default function AccountModal({ onClose, initialTab = 'password' }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState(initialTab);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className="glass-card w-full max-w-3xl flex flex-col max-h-[90vh] overflow-hidden animate-slide-up"
        role="dialog" aria-modal="true"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700/50">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            {t('accountModal.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
            aria-label={t('accountModal.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
          {/* Sidebar tabs */}
          <nav className="md:w-56 shrink-0 md:border-r border-b md:border-b-0 border-gray-200 dark:border-slate-700/50 p-3 md:overflow-y-auto flex md:block gap-1 md:gap-0 overflow-x-auto">
            {TABS.map((tb) => {
              const Icon = tb.icon;
              return (
                <button
                  key={tb.id}
                  onClick={() => setTab(tb.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm w-full text-left transition-colors mb-0.5 whitespace-nowrap ${
                    tab === tb.id
                      ? 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300'
                      : 'text-slate-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  {t(tb.labelKey)}
                </button>
              );
            })}
          </nav>

          {/* Tab body */}
          <div className="flex-1 p-6 overflow-y-auto">
            {tab === 'password' && <PasswordTab onClose={onClose} />}
            {tab === 'username' && <UsernameTab onClose={onClose} />}
            {tab === 'affiliation' && <AffiliationTab onClose={onClose} />}
            {tab === 'security' && <SecurityTab onClose={onClose} />}
          </div>
        </div>
      </div>
    </div>
  );
}


function PasswordTab({ onClose }) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [show, setShow] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.next !== form.confirm) {
      toast.error(t('accountModal.toastMismatch'));
      return;
    }
    if (form.next.length < 4) {
      toast.error(t('accountModal.toastTooShort'));
      return;
    }
    setSubmitting(true);
    try {
      await changePassword({ current_password: form.current, new_password: form.next });
      toast.success(t('accountModal.toastPasswordUpdated'));
      onClose?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('accountModal.toastFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <KeyRound className="w-5 h-5 text-violet-500" />
        {t('accountModal.passwordTitle')}
      </h3>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.currentPassword')}
        </label>
        <input
          type={show ? 'text' : 'password'}
          className="input-field"
          value={form.current}
          onChange={(e) => setForm({ ...form, current: e.target.value })}
          required
          autoComplete="current-password"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.newPassword')}
        </label>
        <div className="relative">
          <input
            type={show ? 'text' : 'password'}
            className="input-field pr-10"
            value={form.next}
            onChange={(e) => setForm({ ...form, next: e.target.value })}
            required
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700 dark:hover:text-gray-200"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.confirmPassword')}
        </label>
        <input
          type={show ? 'text' : 'password'}
          className="input-field"
          value={form.confirm}
          onChange={(e) => setForm({ ...form, confirm: e.target.value })}
          required
          autoComplete="new-password"
        />
      </div>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? t('accountModal.saving') : t('accountModal.savePassword')}
      </button>
    </form>
  );
}


function UsernameTab({ onClose }) {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const [next, setNext] = useState(user?.username || '');
  const [pw, setPw] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await changeUsername({ current_password: pw, new_username: next });
      // Optimistic local update — next /me fetch will canonicalise.
      setUser?.((u) => (u ? { ...u, username: next } : u));
      toast.success(t('accountModal.toastUsernameUpdated'));
      onClose?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('accountModal.toastFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <UserCog className="w-5 h-5 text-violet-500" />
        {t('accountModal.usernameTitle')}
      </h3>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.newUsername')}
        </label>
        <input
          className="input-field"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.currentPassword')}
        </label>
        <input
          type="password"
          className="input-field"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          required
          autoComplete="current-password"
        />
      </div>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? t('accountModal.saving') : t('accountModal.saveUsername')}
      </button>
    </form>
  );
}


function AffiliationTab({ onClose }) {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const [affiliations, setAffiliations] = useState([]);
  const [chosen, setChosen] = useState(user?.solo_affiliation_id || '');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listAffiliations()
      .then((r) => { if (!cancelled) setAffiliations(r.data || []); })
      .catch(() => { /* affiliations are optional */ });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await setMySoloAffiliation(chosen ? Number(chosen) : null);
      setUser?.((u) => (u ? { ...u, solo_affiliation_id: chosen ? Number(chosen) : null } : u));
      toast.success(t('accountModal.toastAffiliationUpdated'));
      onClose?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('accountModal.toastFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <Building2 className="w-5 h-5 text-violet-500" />
        {t('accountModal.affiliationTitle')}
      </h3>
      <p className="text-sm text-slate-500 dark:text-gray-400">
        {t('accountModal.affiliationHint')}
      </p>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1 dark:text-gray-300">
          {t('accountModal.affiliationLabel')}
        </label>
        <select
          className="input-field"
          value={chosen || ''}
          onChange={(e) => setChosen(e.target.value)}
        >
          <option value="">{t('accountModal.affiliationNone')}</option>
          {affiliations.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? t('accountModal.saving') : t('accountModal.saveAffiliation')}
      </button>
    </form>
  );
}


function SecurityTab({ onClose }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <div className="space-y-4 max-w-md">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <ShieldCheck className={`w-5 h-5 ${user?.totp_enabled ? 'text-emerald-500' : 'text-violet-500'}`} />
        {t('accountModal.securityTitle')}
      </h3>
      <p className="text-sm text-slate-500 dark:text-gray-400">
        {user?.totp_enabled
          ? t('accountModal.securityEnabled')
          : t('accountModal.securityDisabled')}
      </p>
      <Link to="/security" onClick={onClose} className="btn-primary inline-block">
        {t('accountModal.openSecurityPage')}
      </Link>
    </div>
  );
}
