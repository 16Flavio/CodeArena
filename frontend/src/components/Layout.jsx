import { Outlet, NavLink, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import {
  LayoutDashboard, Users, Shield, LogOut, Menu, Zap, Sun, Moon, Globe, Mail, FileText, ShieldCheck, GraduationCap, UserRound, ChevronLeft, ChevronsRight,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getIncomingRequestsCount, resendVerification } from '../api';
import AccountModal from './AccountModal';
import NotificationsBell from './NotificationsBell';
import SessionWarning from './SessionWarning';
import toast from 'react-hot-toast';

// Persist the collapsed-sidebar preference per user — reading it on
// load avoids a flash from expanded → collapsed during render.
const SIDEBAR_KEY = 'codearena-sidebar-collapsed';
function readSidebarPref() {
  try { return localStorage.getItem(SIDEBAR_KEY) === '1'; } catch { return false; }
}
function writeSidebarPref(collapsed) {
  try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch { /* ignore */ }
}

const POLL_MS = 30000;

export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(readSidebarPref);
  const [pendingRequests, setPendingRequests] = useState(0);
  const [showAccountModal, setShowAccountModal] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      writeSidebarPref(!c);
      return !c;
    });
  };

  const handleResendVerification = async () => {
    try {
      const r = await resendVerification();
      toast.success(r.data?.detail || t('nav.toastVerificationSent'));
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };
  const currentLng = (i18n.resolvedLanguage || i18n.language || 'fr').slice(0, 2);
  const toggleLng = () => i18n.changeLanguage(currentLng === 'fr' ? 'en' : 'fr');

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await getIncomingRequestsCount();
        if (!cancelled) setPendingRequests(r.data?.pending ?? 0);
      } catch {
        /* ignore */
      }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    const onFocus = () => tick();
    window.addEventListener('focus', onFocus);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') },
    { to: '/teams', icon: Users, label: t('nav.teams'), badge: pendingRequests },
    { to: '/my-submissions', icon: FileText, label: t('nav.mySubmissions') },
    { to: '/learn', icon: GraduationCap, label: t('nav.learn') },
  ];

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
      isActive
        ? 'bg-violet-600/15 text-violet-700 border border-violet-500/30 dark:bg-violet-600/20 dark:text-violet-300'
        : 'text-slate-600 hover:text-slate-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800/50'
    }`;

  return (
    <div className="min-h-screen flex">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen bg-white border-r border-gray-200 flex flex-col transition-all duration-300 dark:bg-slate-950 dark:border-slate-800/50 ${
          collapsed ? 'w-16' : 'w-64'
        } ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        <div className={`flex items-center gap-3 ${collapsed ? 'p-3 justify-center' : 'p-6'}`}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0">
            <Zap className="w-5 h-5 text-white" />
          </div>
          {!collapsed && <span className="text-lg font-bold gradient-text">CodeArena</span>}
          {!collapsed && (
            <button
              onClick={toggleCollapsed}
              className="ml-auto p-1.5 rounded-lg text-slate-400 hover:bg-gray-100 hover:text-slate-700 transition-colors hidden lg:block dark:hover:bg-slate-800 dark:text-gray-500 dark:hover:text-gray-200"
              aria-label={t('nav.collapseSidebar')}
              title={t('nav.collapseSidebar')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* In collapsed mode, the only visible chrome is icons. The
            ChevronsRight expand button sits below the logo so the
            user has somewhere to click to bring labels back. */}
        {collapsed && (
          <button
            onClick={toggleCollapsed}
            className="mx-auto mb-2 p-1.5 rounded-lg text-slate-400 hover:bg-gray-100 hover:text-slate-700 hidden lg:block dark:hover:bg-slate-800 dark:text-gray-500 dark:hover:text-gray-200"
            aria-label={t('nav.expandSidebar')}
            title={t('nav.expandSidebar')}
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        )}

        <nav className={`flex-1 ${collapsed ? 'px-2' : 'px-4'} space-y-1`}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={linkClass}
              onClick={() => setSidebarOpen(false)}
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="flex-1">{item.label}</span>}
              {item.badge > 0 && !collapsed && (
                <span
                  className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-violet-600 text-white text-[11px] font-bold"
                  title={t('nav.pendingRequests', { count: item.badge })}
                >
                  {item.badge > 99 ? '99+' : item.badge}
                </span>
              )}
              {item.badge > 0 && collapsed && (
                <span
                  className="absolute top-0 right-0 w-2 h-2 rounded-full bg-violet-600"
                  title={t('nav.pendingRequests', { count: item.badge })}
                />
              )}
            </NavLink>
          ))}

          {user?.is_admin && (
            <>
              <NavLink
                to="/admin"
                className={linkClass}
                onClick={() => setSidebarOpen(false)}
                title={collapsed ? t('nav.admin') : undefined}
              >
                <Shield className="w-4 h-4 shrink-0" />
                {!collapsed && <span className="flex-1">{t('nav.admin')}</span>}
              </NavLink>
              <NavLink
                to="/admin/learning"
                className={linkClass}
                onClick={() => setSidebarOpen(false)}
                title={collapsed ? t('admin.learning.title') : undefined}
              >
                <GraduationCap className="w-4 h-4 shrink-0" />
                {!collapsed && <span className="flex-1">{t('admin.learning.title')}</span>}
              </NavLink>
            </>
          )}
        </nav>

        <div className={`${collapsed ? 'p-2' : 'p-4'} border-t border-gray-200 dark:border-slate-800/50 space-y-1`}>
          {/* Theme + language toggles. In collapsed mode they shrink
              to icon-only buttons; in expanded mode they show a label. */}
          <button
            onClick={toggleTheme}
            className={`flex items-center ${collapsed ? 'justify-center w-full p-2' : 'gap-3 w-full px-4 py-2.5'} rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-gray-100 transition-all duration-200 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800/50`}
            aria-label={t('nav.toggleTheme')}
            title={collapsed ? (theme === 'dark' ? t('nav.lightMode') : t('nav.darkMode')) : undefined}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {!collapsed && (
              <span className="flex-1 text-left">
                {theme === 'dark' ? t('nav.lightMode') : t('nav.darkMode')}
              </span>
            )}
          </button>

          <button
            onClick={toggleLng}
            className={`flex items-center ${collapsed ? 'justify-center w-full p-2' : 'gap-3 w-full px-4 py-2.5'} rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-gray-100 transition-all duration-200 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800/50`}
            aria-label={t('nav.language')}
            title={collapsed ? t('nav.language') : t('nav.language')}
          >
            <Globe className="w-4 h-4" />
            {!collapsed && (
              <span className="flex-1 text-left uppercase font-mono tabular-nums">{currentLng}</span>
            )}
          </button>

          {/* Single account entry — opens a centered, tabbed modal
              with password / username / affiliation / security. The
              previous 3-button cramming in the sidebar was the
              "tout petit dans le côté" complaint. */}
          <button
            onClick={() => setShowAccountModal(true)}
            className={`flex items-center ${collapsed ? 'justify-center w-full p-2' : 'gap-3 w-full px-3 py-2'} rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-gray-100 transition-all duration-200 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800/50`}
            title={collapsed ? t('nav.account') : undefined}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center text-sm font-bold text-white shrink-0">
              {user?.username?.[0]?.toUpperCase() || <UserRound className="w-4 h-4" />}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-slate-900 truncate dark:text-gray-200">
                  {user?.username}
                </p>
                <p className="text-xs text-slate-500 truncate dark:text-gray-500">{t('nav.account')}</p>
              </div>
            )}
            {!collapsed && user?.totp_enabled && (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" title={t('nav.security')} />
            )}
          </button>

          {user && !user.email_verified && (
            <button
              onClick={handleResendVerification}
              className={`flex items-center ${collapsed ? 'justify-center w-full p-2' : 'gap-3 w-full px-4 py-2.5'} rounded-xl text-sm font-medium text-amber-700 hover:bg-amber-500/10 transition-all duration-200 dark:text-amber-400`}
              title={collapsed ? t('nav.resendVerification') : t('nav.unverifiedTitle')}
            >
              <Mail className="w-4 h-4" />
              {!collapsed && <span className="flex-1 text-left">{t('nav.resendVerification')}</span>}
            </button>
          )}

          <button
            onClick={handleLogout}
            className={`flex items-center ${collapsed ? 'justify-center w-full p-2' : 'gap-3 w-full px-4 py-2.5'} rounded-xl text-sm text-slate-600 hover:text-red-600 hover:bg-red-500/10 transition-all duration-200 dark:text-gray-400 dark:hover:text-red-400`}
            title={collapsed ? t('nav.signOut') : undefined}
          >
            <LogOut className="w-4 h-4" />
            {!collapsed && t('nav.signOut')}
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <SessionWarning />
        <header className="lg:hidden sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-gray-200 px-4 py-3 flex items-center justify-between dark:bg-slate-950/80 dark:border-slate-800/50">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors dark:hover:bg-slate-800"
            aria-label={t('nav.openMenu')}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-violet-500" />
            <span className="font-bold gradient-text">CodeArena</span>
          </div>
          <div className="flex items-center gap-1">
            <NotificationsBell />
            <button
              onClick={toggleLng}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors dark:hover:bg-slate-800 text-xs font-semibold uppercase"
              aria-label={t('nav.language')}
            >
              {currentLng}
            </button>
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors dark:hover:bg-slate-800"
              aria-label={t('nav.toggleTheme')}
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </header>

        <div className="hidden lg:flex justify-end px-8 pt-4">
          <NotificationsBell />
        </div>

        <main className="p-6 lg:p-8 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Sibling of the <aside> — NOT a child. Rendering inside the
          sidebar would inherit its transform-induced containing block,
          which clips the modal's ``fixed inset-0`` to a 256-px slice
          and makes it look like nothing happened on click. */}
      {showAccountModal && <AccountModal onClose={() => setShowAccountModal(false)} />}
    </div>
  );
}
