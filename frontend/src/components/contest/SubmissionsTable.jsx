import { useState, Fragment } from 'react';
import { FileDown, CheckCircle, XCircle, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { downloadMySubmission } from '../../api';
import { formatScore, formatScoreFull } from '../../utils/format';

// Paginated "recent submissions" table with expandable error-detail rows
// and per-submission download. Pagination state lives in the parent (the
// fetch effect and post-submit refresh drive it); ``pageSize`` matches the
// parent's SUBMISSION_PAGE_SIZE.
export default function SubmissionsTable({
  submissions, submissionsTotal, submissionPage, setSubmissionPage, pageSize,
}) {
  const { t } = useTranslation();
  // Submission id whose error detail row is expanded, or null.
  const [expandedErrorId, setExpandedErrorId] = useState(null);

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
          {t('contest.recentSubmissions')}
          <span className="ml-2 text-sm font-normal text-slate-500 dark:text-gray-500">
            ({submissionsTotal})
          </span>
        </h2>
        {submissionsTotal > pageSize && (
          <div className="flex items-center gap-2 text-sm">
            <button
              className="btn-secondary text-xs py-1 px-2"
              disabled={submissionPage === 0}
              onClick={() => setSubmissionPage((p) => Math.max(0, p - 1))}
            >
              {t('common.previous')}
            </button>
            <span className="text-slate-500 dark:text-gray-500">
              {submissionPage * pageSize + 1}
              –
              {Math.min(submissionsTotal, (submissionPage + 1) * pageSize)}
              {' '}/ {submissionsTotal}
            </span>
            <button
              className="btn-secondary text-xs py-1 px-2"
              disabled={(submissionPage + 1) * pageSize >= submissionsTotal}
              onClick={() => setSubmissionPage((p) => p + 1)}
            >
              {t('common.next')}
            </button>
          </div>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-700/50">
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableInstance')}</th>
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableFile')}</th>
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableScore')}</th>
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableStatus')}</th>
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableBy')}</th>
              <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableTime')}</th>
              <th className="text-right text-slate-500 font-medium pb-3 dark:text-gray-400">{t('mySubmissions.colActions')}</th>
            </tr>
          </thead>
          <tbody>
            {submissions.map((s) => (
              <Fragment key={s.id}>
              <tr className="border-b border-gray-100 hover:bg-gray-50 dark:border-slate-800/30 dark:hover:bg-slate-800/20">
                <td className="py-3 pr-4 text-slate-800 max-w-[200px] truncate dark:text-gray-200" title={s.instance_name}>
                  {s.instance_name}
                </td>
                <td className="py-3 pr-4 text-slate-500 font-mono text-xs max-w-[200px] truncate dark:text-gray-400" title={s.file_name}>
                  {s.file_name}
                </td>
                <td className="py-3 pr-4">
                  <span
                    className="font-mono font-bold text-violet-600 tabular-nums dark:text-violet-300"
                    title={formatScoreFull(s.score)}
                  >
                    {formatScore(s.score)}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  {s.status === 'scored' ? (
                    <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle className="w-3.5 h-3.5" /> {t('contest.statusScored')}
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setExpandedErrorId(expandedErrorId === s.id ? null : s.id)}
                      className={`inline-flex items-center gap-1 text-red-600 rounded px-1 -mx-1 hover:bg-red-500/10 dark:text-red-400 ${
                        expandedErrorId === s.id ? 'bg-red-500/10 ring-1 ring-red-500/30' : ''
                      }`}
                      title={t('contest.clickForErrorDetail')}
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      {s.status === 'invalid_output' ? t('contest.statusInvalidOutput') : t('contest.statusError')}
                      <ChevronDown className={`w-3 h-3 transition-transform ${expandedErrorId === s.id ? 'rotate-180' : ''}`} />
                    </button>
                  )}
                </td>
                <td className="py-3 pr-4 text-slate-500 dark:text-gray-400">{s.submitted_by_username}</td>
                <td className="py-3 pr-4 text-slate-400 text-xs dark:text-gray-500">
                  {new Date(s.submitted_at).toLocaleString()}
                </td>
                <td className="py-3 text-right">
                  <div className="inline-flex items-center gap-1">
                    <button
                      type="button"
                      onClick={async () => {
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
                      }}
                      className="p-1.5 rounded hover:bg-gray-100 text-violet-600 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300 dark:hover:bg-slate-800 transition-colors"
                      title={t('mySubmissions.download')}
                      aria-label={t('mySubmissions.download')}
                    >
                      <FileDown className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
              {expandedErrorId === s.id && s.status !== 'scored' && (
                <tr className="border-b border-gray-100 bg-red-500/5 dark:border-slate-800/30 dark:bg-red-500/10">
                  <td colSpan={7} className="px-4 py-3">
                    <p className="text-[10px] uppercase text-red-600 mb-1 dark:text-red-400">
                      {s.status === 'invalid_output'
                        ? t('contest.invalidOutputTitle')
                        : t('contest.scoringErrorTitle')}
                    </p>
                    <pre className="text-xs font-mono text-red-700 whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:text-red-300">
                      {s.error_message || t('contest.genericScoringError')}
                    </pre>
                  </td>
                </tr>
              )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
