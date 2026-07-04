import { useState, useEffect, useMemo } from 'react';
import {
  Package, Download, Trash2, AlertTriangle, Search, Terminal, RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import {
  getPackages, getPackageEnvInfo, installPackage, uninstallPackage,
} from '../api';
import { useConfirm } from './Confirm';
import { extractErrorMessage } from '../utils/apiError';

export default function PackagesPanel() {
  const confirm = useConfirm();
  const [packages, setPackages] = useState([]);
  const [envInfo, setEnvInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [installSpec, setInstallSpec] = useState('');
  const [installing, setInstalling] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [lastOutput, setLastOutput] = useState(null);
  const { t } = useTranslation();

  const refresh = async () => {
    try {
      const [list, info] = await Promise.all([getPackages(), getPackageEnvInfo()]);
      setPackages(list.data);
      setEnvInfo(info.data);
    } catch {
      toast.error(t('packages.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleInstall = async (e) => {
    e.preventDefault();
    const spec = installSpec.trim();
    if (!spec) return;
    setInstalling(true);
    setLastOutput(null);
    const toastId = toast.loading(t('packages.installing_', { spec }));
    try {
      const { data } = await installPackage(spec);
      setLastOutput({ ok: data.ok, title: data.detail, body: data.output });
      if (data.ok) {
        toast.success(data.detail, { id: toastId });
        setInstallSpec('');
        await refresh();
      } else {
        toast.error(data.detail, { id: toastId });
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, t('packages.installFailed')), { id: toastId });
    } finally {
      setInstalling(false);
    }
  };

  const handleUninstall = async (pkg) => {
    const message = pkg.is_core
      ? t('packages.confirmRemoveCore', { name: pkg.name })
      : t('packages.confirmRemove', { name: pkg.name });
    const ok = await confirm({ message, danger: true });
    if (!ok) return;

    setRemoving(pkg.name);
    setLastOutput(null);
    const toastId = toast.loading(t('packages.removing', { name: pkg.name }));
    try {
      const { data } = await uninstallPackage(pkg.name);
      setLastOutput({ ok: data.ok, title: data.detail, body: data.output });
      if (data.ok) {
        toast.success(data.detail, { id: toastId });
        await refresh();
      } else {
        toast.error(data.detail, { id: toastId });
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, t('packages.removeFailed')), { id: toastId });
    } finally {
      setRemoving(null);
    }
  };

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return packages;
    return packages.filter((p) => p.name.toLowerCase().includes(q));
  }, [packages, filter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-accent-500/15 flex items-center justify-center flex-shrink-0">
              <Package className="w-5 h-5 text-accent-600 dark:text-accent-300" />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-zinc-500 dark:text-zinc-400">{t('packages.python')}</p>
              <p className="font-mono text-sm text-zinc-900 dark:text-white">
                {envInfo?.python_version || '-'}
              </p>
              <p className="font-mono text-xs text-zinc-400 truncate dark:text-zinc-500" title={envInfo?.python_executable}>
                {envInfo?.python_executable}
              </p>
            </div>
          </div>
          <button
            onClick={refresh}
            className="btn-secondary text-sm py-2 px-3"
            title={t('packages.refreshTitle')}
            aria-label={t('packages.refreshTitle')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-zinc-500 mt-4 leading-relaxed dark:text-zinc-500">
          {t('packages.hint', { mods: 'math, re, json' })}
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-700 mb-3 flex items-center gap-2 dark:text-zinc-300">
          <Download className="w-4 h-4 text-accent-500 dark:text-accent-400" />
          {t('packages.installSection')}
        </h3>
        <form onSubmit={handleInstall} className="flex flex-wrap gap-3 items-start">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              className="input-field font-mono text-sm py-2"
              placeholder={t('packages.installPlaceholder')}
              value={installSpec}
              onChange={(e) => setInstallSpec(e.target.value)}
              disabled={installing}
              spellCheck={false}
            />
            <p className="text-xs text-zinc-400 mt-1.5 dark:text-zinc-600">
              {t('packages.installHint')}
            </p>
          </div>
          <button
            type="submit"
            className="btn-primary text-sm py-2"
            disabled={installing || !installSpec.trim()}
          >
            {installing ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t('packages.installing')}
              </span>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2 inline" />
                {t('packages.install')}
              </>
            )}
          </button>
        </form>
      </div>

      {lastOutput && (
        <div
          className={`card p-4 border ${
            lastOutput.ok ? 'border-emerald-500/30' : 'border-red-500/30'
          }`}
        >
          <div className="flex items-start gap-2 mb-2">
            <Terminal className={`w-4 h-4 mt-0.5 ${lastOutput.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`} />
            <p className={`text-sm font-medium ${lastOutput.ok ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'}`}>
              {lastOutput.title}
            </p>
          </div>
          <pre className="text-xs font-mono text-zinc-600 whitespace-pre-wrap break-all max-h-60 overflow-y-auto bg-zinc-100 rounded-lg p-3 dark:text-zinc-400 dark:bg-zinc-900/50">
            {lastOutput.body || t('packages.noOutput')}
          </pre>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="p-4 border-b border-zinc-200 flex flex-wrap items-center justify-between gap-3 dark:border-zinc-800/50">
          <h3 className="text-sm font-semibold text-zinc-700 flex items-center gap-2 dark:text-zinc-300">
            <Package className="w-4 h-4 text-accent-500 dark:text-accent-400" />
            {t('packages.installedHeading')}
            <span className="text-xs font-normal text-zinc-400 dark:text-zinc-500">({filtered.length})</span>
          </h3>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none dark:text-zinc-500" />
            <input
              type="text"
              className="input-field text-sm py-1.5 pl-8 pr-3 w-56"
              placeholder={t('packages.filterPlaceholder')}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="text-zinc-500 text-sm text-center py-10 dark:text-zinc-500">
            {filter ? t('packages.noMatch') : t('packages.noPackages')}
          </p>
        ) : (
          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white/95 dark:bg-zinc-900/95">
                <tr>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-5 dark:text-zinc-400">
                    {t('packages.installedHeading').split(' ')[0]}
                  </th>
                  <th className="text-left text-zinc-500 font-semibold py-2.5 px-5 w-32 dark:text-zinc-400">{t('packages.colVersion')}</th>
                  <th className="text-right text-zinc-500 font-semibold py-2.5 px-5 w-24 dark:text-zinc-400">{t('packages.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.name} className="border-t border-zinc-100 hover:bg-zinc-50 dark:border-zinc-800/30 dark:hover:bg-zinc-800/20">
                    <td className="py-2.5 px-5 font-mono text-zinc-800 dark:text-zinc-200">
                      <div className="flex items-center gap-2">
                        {p.name}
                        {p.is_core && (
                          <span
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-400"
                            title={t('packages.coreTooltip')}
                          >
                            <AlertTriangle className="w-3 h-3" />
                            {t('packages.coreLabel')}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-5 font-mono text-zinc-500 text-xs dark:text-zinc-400">{p.version}</td>
                    <td className="py-2.5 px-5 text-right">
                      <button
                        onClick={() => handleUninstall(p)}
                        disabled={removing === p.name}
                        className="p-1.5 rounded-lg transition-colors text-zinc-400 hover:bg-red-500/10 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed dark:text-zinc-400 dark:hover:text-red-400"
                        title={p.is_core ? t('packages.uninstallWarn') : t('packages.uninstall')}
                        aria-label={t('packages.uninstall')}
                      >
                        {removing === p.name ? (
                          <div className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
