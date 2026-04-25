import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { Download, CheckCircle, XCircle, FileText, GitCompare } from 'lucide-react';
import { getMySubmissions, downloadMySubmission } from '../api';
import { formatScore, formatScoreFull } from '../utils/format';
import { formatDateTime } from '../utils/datetime';
import DiffModal from '../components/DiffModal';

export default function MySubmissions() {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  // "output" (Hashcode instances) | "icpc" (source submissions against problems).
  // Admin uses the same toggle on /admin — we mirror it here so the user
  // never sees a mixed table where half the columns are meaningless.
  const [kind, setKind] = useState('output');
  const [selected, setSelected] = useState([]);
  const [diffPair, setDiffPair] = useState(null);

  const toggleSelected = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  useEffect(() => {
    getMySubmissions(100)
      .then((r) => setItems(r.data || []))
      .catch(() => toast.error(t('mySubmissions.loadFailed')))
      .finally(() => setLoading(false));
    // ``t`` is intentionally absent — re-fetching submissions when the
    // user toggles the language is wasteful (the backend payload is
    // language-agnostic). The closure does call ``t`` on error, but it
    // captures the latest reference at toast time via i18next.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Split once — the backend endpoint returns everything and we bucket
  // client-side. Small enough (up to 100 rows) that filtering locally is
  // cheaper than two round trips.
  const icpcItems = useMemo(() => items.filter((s) => s.problem_id != null), [items]);
  const outputItems = useMemo(() => items.filter((s) => s.instance_id != null), [items]);
  const visible = kind === 'icpc' ? icpcItems : outputItems;

  const stats = useMemo(() => {
    const bucket = (rows) => ({
      total: rows.length,
      pending: rows.filter((s) => s.status === 'pending').length,
      scored: rows.filter((s) => s.status === 'scored').length,
      error: rows.filter((s) => s.status === 'error' || s.status === 'invalid_output').length,
    });
    return { icpc: bucket(icpcItems), output: bucket(outputItems) };
  }, [icpcItems, outputItems]);

  const handleDownload = async (s) => {
    try {
      const res = await downloadMySubmission(s.id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = s.file_name || `submission_${s.id}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t('mySubmissions.downloadFailed'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const s = kind === 'icpc' ? stats.icpc : stats.output;
  const pills = [
    { k: 'total', v: s.total, cls: 'bg-slate-500/10 text-slate-700 dark:text-gray-300' },
    { k: 'pending', v: s.pending, cls: 'bg-amber-500/10 text-amber-700 dark:text-amber-300' },
    { k: 'scored', v: s.scored, cls: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
    { k: 'error', v: s.error, cls: 'bg-red-500/10 text-red-700 dark:text-red-300' },
  ];

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">{t('mySubmissions.title')}</h1>
          <p className="text-slate-500 dark:text-gray-400 mt-1">{t('mySubmissions.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="inline-flex rounded-lg border border-gray-200 p-0.5 dark:border-slate-700">
            <button
              type="button"
              onClick={() => { setKind('output'); setSelected([]); }}
              className={`text-xs font-medium px-3 py-1 rounded-md transition-colors ${
                kind === 'output'
                  ? 'bg-violet-600 text-white'
                  : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              {t('admin.submissions.kindOutput')} <span className="opacity-60">({stats.output.total})</span>
            </button>
            <button
              type="button"
              onClick={() => { setKind('icpc'); setSelected([]); }}
              className={`text-xs font-medium px-3 py-1 rounded-md transition-colors ${
                kind === 'icpc'
                  ? 'bg-violet-600 text-white'
                  : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              {t('admin.submissions.kindIcpc')} <span className="opacity-60">({stats.icpc.total})</span>
            </button>
          </div>
          {kind === 'output' && (
            <button
              type="button"
              disabled={selected.length !== 2}
              onClick={() => setDiffPair([selected[0], selected[1]])}
              className="btn-primary text-sm disabled:opacity-50"
            >
              <GitCompare className="w-4 h-4 mr-2 inline" />
              {t('mySubmissions.compare', { count: selected.length })}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-[11px]">
        {pills.map((p) => (
          <span key={p.k} className={`px-2 py-0.5 rounded ${p.cls} font-mono`}>
            {t(`admin.submissions.stat_${p.k}`)}: <strong>{p.v}</strong>
          </span>
        ))}
      </div>

      <div className="glass-card p-6">
        {visible.length === 0 ? (
          <div className="py-12 text-center text-slate-500 dark:text-gray-500">
            <FileText className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>{t('mySubmissions.empty')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700/50">
                  {kind === 'output' && <th className="pb-3 pr-2 w-6"></th>}
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('mySubmissions.colContest')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">
                    {kind === 'icpc' ? t('admin.submissions.colProblem') : t('mySubmissions.colInstance')}
                  </th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">
                    {kind === 'icpc' ? t('admin.submissions.colVerdict') : t('mySubmissions.colScore')}
                  </th>
                  {kind === 'output' && (
                    <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('mySubmissions.colStatus')}</th>
                  )}
                  {kind === 'icpc' && (
                    <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('mySubmissions.colLanguage')}</th>
                  )}
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('mySubmissions.colWhen')}</th>
                  <th className="text-right text-slate-500 font-medium pb-3 dark:text-gray-400">{t('mySubmissions.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((s) => (
                  <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50 dark:border-slate-800/30 dark:hover:bg-slate-800/20">
                    {kind === 'output' && (
                      <td className="py-3 pr-2">
                        <input
                          type="checkbox"
                          checked={selected.includes(s.id)}
                          onChange={() => toggleSelected(s.id)}
                          aria-label={t('mySubmissions.selectForCompare')}
                        />
                      </td>
                    )}
                    <td className="py-3 pr-4 max-w-[220px] truncate dark:text-gray-200">
                      <Link to={`/contests/${s.contest_id}`} className="text-violet-600 hover:underline dark:text-violet-300">
                        {s.contest_title}
                      </Link>
                    </td>
                    <td className="py-3 pr-4 text-slate-800 dark:text-gray-200">
                      {kind === 'icpc' ? (s.problem_label || '—') : (s.instance_name || '—')}
                    </td>
                    <td className="py-3 pr-4">
                      {kind === 'icpc' ? (
                        s.latest_verdict ? (
                          <span className={
                            s.latest_verdict === 'AC'
                              ? 'inline-flex items-center gap-1 text-emerald-600 font-mono dark:text-emerald-400'
                              : 'inline-flex items-center gap-1 text-red-600 font-mono dark:text-red-400'
                          }>
                            {s.latest_verdict}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono">{s.status}</span>
                        )
                      ) : (
                        <span className="font-mono font-bold text-violet-600 tabular-nums dark:text-violet-300" title={formatScoreFull(s.score)}>
                          {formatScore(s.score)}
                        </span>
                      )}
                    </td>
                    {kind === 'output' && (
                      <td className="py-3 pr-4">
                        {s.status === 'scored' ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                            <CheckCircle className="w-3.5 h-3.5" /> {t('contest.statusScored')}
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 text-red-600 cursor-help dark:text-red-400"
                            title={s.error_message || t('contest.genericScoringError')}
                          >
                            <XCircle className="w-3.5 h-3.5" /> {t('contest.statusError')}
                          </span>
                        )}
                      </td>
                    )}
                    {kind === 'icpc' && (
                      <td className="py-3 pr-4 text-xs font-mono text-slate-500 dark:text-gray-400">
                        {s.source_language || '—'}
                      </td>
                    )}
                    <td className="py-3 pr-4 text-slate-400 text-xs dark:text-gray-500">
                      {formatDateTime(s.submitted_at)}
                    </td>
                    <td className="py-3 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleDownload(s)}
                          className="p-1.5 rounded hover:bg-gray-100 text-violet-600 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300 dark:hover:bg-slate-800 transition-colors"
                          title={t('mySubmissions.download')}
                          aria-label={t('mySubmissions.download')}
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {diffPair && (
        <DiffModal leftId={diffPair[0]} rightId={diffPair[1]} onClose={() => setDiffPair(null)} />
      )}
    </div>
  );
}
