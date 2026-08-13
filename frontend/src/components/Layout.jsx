import { Outlet, NavLink, useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';
import {
  LayoutDashboard, Users, Shield, LogOut, Menu, X, Zap, Sun, Moon, Mail,
  FileText, ShieldCheck, GraduationCap, Medal, UserRound, ChevronDown, Trophy,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getIncomingRequestsCount, resendVerification } from '../api';
import AccountModal from './AccountModal';
import NotificationsBell from './NotificationsBell';
import SessionWarning from './SessionWarning';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../utils/apiError';

const POLL_MS = 30000;

// Product-style shell: a sticky top navigation bar (brand, primary nav,
// utilities and account on the right) instead of the old admin-template
// sidebar. Mobile gets a slide-down sheet with the same entries.
export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [pendingRequests, setPendingRequests] = useState(0);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const accountRef = useRef(null);

  const handleResendVerification = async () => {
    try {
      const r = await resendVerification();
      toast.success(r.data?.detail || t('nav.toastVerificationSent'));
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
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

  // Close the account menu on any outside click or Escape.
  useEffect(() => {
    if (!accountOpen) return undefined;
    const onClick = (e) => {
      if (accountRef.current && !accountRef.current.contains(e.target)) {
        setAccountOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setAccountOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [accountOpen]);

  // Any navigation closes the mobile sheet and the account menu - the
  // sheet's own links do it onClick, but the brand link and the
  // notification items navigate too.
  const { pathname } = useLocation();
  useEffect(() => {
    setMenuOpen(false);
    setAccountOpen(false);
  }, [pathname]);

  // Escape closes the mobile sheet as well.
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') },
    { to: '/contests', icon: Trophy, label: t('nav.contests') },
    { to: '/teams', icon: Users, label: t('nav.teams'), badge: pendingRequests },
    { to: '/my-submissions', icon: FileText, label: t('nav.mySubmissions') },
    { to: '/learn', icon: GraduationCap, label: t('nav.learn') },
    { to: '/league', icon: Medal, label: t('nav.league') },
  ];
  const adminItems = user?.is_admin
    ? [
        { to: '/admin', icon: Shield, label: t('nav.admin') },
        { to: '/admin/learning', icon: GraduationCap, label: t('admin.learning.title') },
      ]
    : [];

  // Top-bar links: quiet text, active state = ink text + a 2px accent
  // rule sitting on the header's bottom border.
  const topLinkClass = ({ isActive }) =>
    `relative flex items-center gap-1.5 px-1 h-16 text-sm font-medium whitespace-nowrap transition-colors ${
      isActive
        ? 'text-zinc-900 dark:text-white after:absolute after:left-0 after:right-0 after:-bottom-px after:h-0.5 after:rounded-full after:bg-accent-600 dark:after:bg-accent-400'
        : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
    }`;

  const sheetLinkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-accent-600/10 text-accent-700 dark:bg-accent-500/15 dark:text-accent-300'
        : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800/60'
    }`;

  const iconBtn =
    'p-2 rounded-full text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800';

  return (
    <div className="min-h-screen flex flex-col">
      <SessionWarning />

      <header className="sticky top-0 z-40 bg-white/95 border-b border-zinc-200 dark:bg-zinc-950/95 dark:border-zinc-800">
        <div className="max-w-7xl mx-auto px-4 lg:px-8 h-16 flex items-center gap-6">
          {/* Brand */}
          <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0" aria-label="CodeArena">
            <span className="w-8 h-8 rounded-full bg-accent-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </span>
            <span className="text-[17px] font-bold tracking-tight text-zinc-900 dark:text-white">
              CodeArena
            </span>
          </Link>

          {/* Primary navigation (desktop) */}
          <nav className="hidden xl:flex items-center gap-5 h-16" aria-label={t('nav.primary')}>
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} className={topLinkClass}>
                <span>{item.label}</span>
                {item.badge > 0 && (
                  <span
                    className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-accent-600 text-white text-[10px] font-bold font-mono"
                    title={t('nav.pendingRequests', { count: item.badge })}
                  >
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </NavLink>
            ))}
            {adminItems.length > 0 && (
              <span className="h-5 w-px bg-zinc-200 dark:bg-zinc-800" aria-hidden="true" />
            )}
            {adminItems.map((item) => (
              <NavLink key={item.to} to={item.to} className={topLinkClass}>
                <item.icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Utilities */}
          <div className="ml-auto flex items-center gap-1">
            <NotificationsBell />
            <button onClick={toggleLng} className={`${iconBtn} text-xs font-semibold uppercase font-mono w-9 h-9 flex items-center justify-center`} aria-label={t('nav.language')}>
              {currentLng}
            </button>
            <button onClick={toggleTheme} className={iconBtn} aria-label={t('nav.toggleTheme')}>
              {theme === 'dark' ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
            </button>

            {/* Account menu (desktop) */}
            <div className="relative hidden xl:block" ref={accountRef}>
              <button
                onClick={() => setAccountOpen((o) => !o)}
                className="flex items-center gap-2 pl-1.5 pr-2 py-1.5 ml-1 rounded-full hover:bg-zinc-100 transition-colors dark:hover:bg-zinc-800"
                aria-haspopup="menu"
                aria-expanded={accountOpen}
              >
                <span className="w-7 h-7 rounded-full bg-accent-500 flex items-center justify-center text-[13px] font-bold text-white dark:text-accent-950">
                  {user?.username?.[0]?.toUpperCase() || <UserRound className="w-4 h-4" />}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${accountOpen ? 'rotate-180' : ''}`} />
              </button>
              {accountOpen && (
                <div
                  className="absolute right-0 top-full mt-2 w-60 card p-1.5 shadow-lg shadow-zinc-950/5 dark:shadow-black/30"
                  role="menu"
                >
                  <div className="px-3 py-2.5 border-b border-zinc-100 dark:border-zinc-800 mb-1">
                    <p className="text-sm font-semibold text-zinc-900 truncate dark:text-white flex items-center gap-1.5">
                      {user?.username}
                      {user?.totp_enabled && (
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" title={t('nav.security')} />
                      )}
                    </p>
                    <p className="text-xs text-zinc-500 truncate dark:text-zinc-400">{user?.email}</p>
                  </div>
                  <button
                    onClick={() => { setAccountOpen(false); setShowAccountModal(true); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-zinc-700 hover:bg-zinc-100 transition-colors dark:text-zinc-200 dark:hover:bg-zinc-800"
                    role="menuitem"
                  >
                    <UserRound className="w-4 h-4 text-zinc-400" />
                    {t('nav.account')}
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-zinc-700 hover:bg-red-50 hover:text-red-700 transition-colors dark:text-zinc-200 dark:hover:bg-red-950/40 dark:hover:text-red-400"
                    role="menuitem"
                  >
                    <LogOut className="w-4 h-4 text-zinc-400" />
                    {t('nav.signOut')}
                  </button>
                </div>
              )}
            </div>

            {/* Mobile menu trigger */}
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className={`${iconBtn} xl:hidden`}
              aria-label={t('nav.openMenu')}
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile sheet */}
        {menuOpen && (
          <nav className="xl:hidden border-t border-zinc-200 bg-white px-3 py-3 space-y-0.5 dark:bg-zinc-950 dark:border-zinc-800">
            {[...navItems, ...adminItems].map((item) => (
              <NavLink key={item.to} to={item.to} className={sheetLinkClass} onClick={() => setMenuOpen(false)}>
                <item.icon className="w-4 h-4 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.badge > 0 && (
                  <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-accent-600 text-white text-[11px] font-bold">
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </NavLink>
            ))}
            <div className="border-t border-zinc-200 dark:border-zinc-800 my-2" />
            <button
              onClick={() => { setMenuOpen(false); setShowAccountModal(true); }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition-colors dark:text-zinc-300 dark:hover:bg-zinc-800/60"
            >
              <UserRound className="w-4 h-4" />
              <span className="flex-1 text-left">{user?.username}</span>
              {user?.totp_enabled && <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />}
            </button>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-zinc-600 hover:bg-red-50 hover:text-red-700 transition-colors dark:text-zinc-300 dark:hover:bg-red-950/40 dark:hover:text-red-400"
            >
              <LogOut className="w-4 h-4" />
              {t('nav.signOut')}
            </button>
          </nav>
        )}
      </header>

      {/* Unverified-email notice: a proper banner instead of a nav button. */}
      {user && !user.email_verified && (
        <div className="bg-amber-50 border-b border-amber-200 dark:bg-amber-950/40 dark:border-amber-900">
          <div className="max-w-7xl mx-auto px-4 lg:px-8 py-2 flex items-center gap-3 text-sm text-amber-800 dark:text-amber-300">
            <Mail className="w-4 h-4 shrink-0" />
            <span className="flex-1">{t('nav.unverifiedTitle')}</span>
            <button
              onClick={handleResendVerification}
              className="font-semibold underline underline-offset-2 hover:no-underline shrink-0"
            >
              {t('nav.resendVerification')}
            </button>
          </div>
        </div>
      )}

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 lg:px-8 py-8">
        <Outlet />
      </main>

      {showAccountModal && <AccountModal onClose={() => setShowAccountModal(false)} />}
    </div>
  );
}
