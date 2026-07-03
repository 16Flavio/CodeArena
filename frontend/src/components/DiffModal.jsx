import { useEffect, useState } from 'react';
import { X, GitCompare } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getSubmissionContent } from '../api';
import { diffLines } from '../utils/diff';
import { formatDateTime } from '../utils/datetime';
import { extractErrorMessage } from '../utils/apiError';

export default function DiffModal({ leftId, rightId, onClose }) {
  const { t } = useTranslation();
  const [state, setState] = useState({ loading: true, left: null, right: null, error: null });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSubmissionContent(leftId), getSubmissionContent(rightId)])
      .then(([a, b]) => {
        if (!cancelled) setState({ loading: false, left: a.data, right: b.data, error: null });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            loading: false, left: null, right: null,
            error: extractErrorMessage(err, t('diff.loadFailed')),
          });
        }
      });
    return () => { cancelled = true; };
  }, [leftId, rightId, t]);

  const rows = state.left && state.right
    ? diffLines(state.left.submission_data, state.right.submission_data)
    : [];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="glass-card p-6 w-full max-w-6xl max-h-[90vh] flex flex-col animate-slide-up"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            <GitCompare className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('diff.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
            aria-label={t('accountModal.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {state.loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {state.error && (
          <p className="text-sm text-red-500 py-8 text-center">{state.error}</p>
        )}
        {state.left && state.right && (
          <>
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-500 mb-3 dark:text-gray-400">
              <div>
                <span className="font-mono">{state.left.file_name || `#${state.left.id}`}</span>
                <span className="ml-2">{formatDateTime(state.left.submitted_at)}</span>
              </div>
              <div>
                <span className="font-mono">{state.right.file_name || `#${state.right.id}`}</span>
                <span className="ml-2">{formatDateTime(state.right.submitted_at)}</span>
              </div>
            </div>
            <div className="flex-1 overflow-auto rounded-lg border border-gray-200 dark:border-slate-700/50">
              <table className="w-full text-xs font-mono">
                <tbody>
                  {rows.map((r, idx) => (
                    <tr key={idx}>
                      <td className={`align-top w-1/2 px-3 py-0.5 whitespace-pre-wrap break-all ${
                        r.kind === 'del' ? 'bg-red-500/10 text-red-700 dark:text-red-300' : 'text-slate-700 dark:text-gray-300'
                      }`}>
                        {r.left !== null ? r.left : ''}
                      </td>
                      <td className={`align-top w-1/2 px-3 py-0.5 whitespace-pre-wrap break-all border-l border-gray-200 dark:border-slate-700/50 ${
                        r.kind === 'add' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'text-slate-700 dark:text-gray-300'
                      }`}>
                        {r.right !== null ? r.right : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
