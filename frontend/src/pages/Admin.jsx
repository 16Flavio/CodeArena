import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { Navigate } from 'react-router-dom';
import { getUsers, getContests, getContest } from '../api';
import {
  Users, Trophy, Shield, Package,
  ScrollText, Inbox, Cpu, Building2, Medal,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import PackagesPanel from '../components/PackagesPanel';
import ScoringPanel from '../components/ScoringPanel';
import AffiliationsPanel from '../components/AffiliationsPanel';
import WorkersPanel from '../components/WorkersPanel';
import UsersTab from '../components/admin/UsersTab';
import AuditLogTab from '../components/admin/AuditLogTab';
import SubmissionsTab from '../components/admin/SubmissionsTab';
import ContestsTab from '../components/admin/ContestsTab';
import LeaguesTab from '../components/admin/LeaguesTab';

export default function Admin() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [tab, setTab] = useState('contests');
  // Users + contests live here (not in the tabs) because they're shared:
  // UsersTab renders the user list, ContestsTab needs both (users feed
  // the contest editor's allowlist picker) and SubmissionsTab needs the
  // contests for its filter dropdown.
  const [users, setUsers] = useState([]);
  const [contests, setContests] = useState([]);
  const [loading, setLoading] = useState(true);

  const isAdmin = user?.is_admin;

  const refresh = async () => {
    if (!isAdmin) return;
    try {
      const [u, c] = await Promise.all([getUsers(), getContests()]);
      setUsers(u.data);
      const fullContests = await Promise.all(
        c.data.map((ct) => getContest(ct.id).then((r) => r.data))
      );
      setContests(fullContests);
    } catch {
      toast.error(t('admin.contests.toastLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [isAdmin]);

  if (!isAdmin) return <Navigate to="/dashboard" replace />;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-900 flex items-center gap-3 dark:text-white">
          <Shield className="w-8 h-8 text-amber-500 dark:text-amber-400" />
          {t('admin.title')}
        </h1>
        <p className="text-zinc-500 mt-1 dark:text-zinc-400">{t('admin.subtitle')}</p>
      </div>

      <div className="flex gap-1 bg-white/50 p-1 rounded-lg w-fit border border-zinc-200 dark:bg-zinc-900/50 dark:border-zinc-800/50">
        {[
          { key: 'contests', label: t('admin.tabContests'), icon: Trophy },
          { key: 'leagues', label: t('admin.tabLeagues'), icon: Medal },
          { key: 'submissions', label: t('admin.tabSubmissions'), icon: Inbox },
          { key: 'users', label: t('admin.tabUsers'), icon: Users },
          { key: 'affiliations', label: t('admin.tabAffiliations'), icon: Building2 },
          { key: 'workers', label: t('admin.tabWorkers'), icon: Cpu },
          { key: 'packages', label: t('admin.tabPackages'), icon: Package },
          { key: 'scoring', label: t('admin.tabScoring'), icon: Cpu },
          { key: 'audit', label: t('admin.tabAudit'), icon: ScrollText },
        ].map((tb) => (
          <button
            key={tb.key}
            onClick={() => setTab(tb.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === tb.key
                ? 'bg-accent-600 text-white'
                : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-800/50'
            }`}
          >
            <tb.icon className="w-4 h-4" />
            {tb.label}
          </button>
        ))}
      </div>

      {tab === 'affiliations' && <AffiliationsPanel />}
      {tab === 'workers' && <WorkersPanel />}

      {tab === 'users' && (
        <UsersTab users={users} currentUser={user} onChange={refresh} />
      )}

      {tab === 'contests' && (
        <ContestsTab contests={contests} users={users} onChange={refresh} />
      )}

      {tab === 'leagues' && <LeaguesTab contests={contests} />}

      {tab === 'submissions' && <SubmissionsTab contests={contests} />}
      {tab === 'packages' && <PackagesPanel />}

      {tab === 'scoring' && <ScoringPanel />}

      {tab === 'audit' && <AuditLogTab />}
    </div>
  );
}
