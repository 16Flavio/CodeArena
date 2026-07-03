import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  FileDown, Target, AlertCircle, ChevronDown, ChevronUp, FileType, ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { downloadProblemStatement } from '../../api';
import { extractErrorMessage } from '../../utils/apiError';

// Collapsible problem-statement card: PDF viewer (with blob lifecycle +
// retry) when the contest ships a PDF, markdown fallback otherwise.
// Stays mounted even when ``visible`` is false so the PDF fetch (and its
// 403 toast for gated statements) keeps the same timing as before the
// extraction.
export default function ProblemStatementCard({ contest, visible }) {
  const { t } = useTranslation();
  const [showStatement, setShowStatement] = useState(true);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [pdfRetryCount, setPdfRetryCount] = useState(0);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (!contest?.has_problem_statement_pdf) {
      setPdfBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      return undefined;
    }
    let cancelled = false;
    let createdUrl = null;
    setPdfLoading(true);
    downloadProblemStatement(contest.id)
      .then((r) => {
        if (cancelled) return;
        createdUrl = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
        setPdfBlobUrl(createdUrl);
      })
      .catch(async (err) => {
        if (cancelled) return;
        // 403 = registration or pre-start gate; surface the backend's
        // French message instead of the generic "pdf load failed".
        let msg = t('contest.pdfLoadFailed');
        try {
          if (err.response?.data instanceof Blob) {
            const text = await err.response.data.text();
            const parsed = JSON.parse(text);
            // Re-wrap the parsed blob payload so the shared helper can
            // map coded errors to translations, same as the JSON path.
            msg = extractErrorMessage({ response: { data: parsed } }, msg);
          } else {
            msg = extractErrorMessage(err, msg);
          }
        } catch { /* keep the generic message */ }
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setPdfLoading(false);
      });
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [contest?.id, contest?.has_problem_statement_pdf, pdfRetryCount]);

  if (!visible) return null;

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setShowStatement(!showStatement)}
        className="w-full flex items-center justify-between p-5 hover:bg-zinc-50 transition-colors dark:hover:bg-zinc-800/30"
      >
        <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2 dark:text-white">
          {contest.has_problem_statement_pdf ? (
            <FileType className="w-5 h-5 text-accent-500 dark:text-accent-400" />
          ) : (
            <Target className="w-5 h-5 text-accent-500 dark:text-accent-400" />
          )}
          {t('contest.problemStatement')}
          {contest.has_problem_statement_pdf && (
            <span className="text-xs font-normal text-zinc-400 ml-1 dark:text-zinc-500">{t('contest.pdfBadge')}</span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          {contest.has_problem_statement_pdf && pdfBlobUrl && (
            <a
              href={pdfBlobUrl}
              download={contest.problem_statement_pdf_name || 'enonce.pdf'}
              onClick={(e) => e.stopPropagation()}
              className="text-xs font-medium px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
              title={t('common.download')}
            >
              <FileDown className="w-3.5 h-3.5" />
              {t('common.download')}
            </a>
          )}
          {contest.has_problem_statement_pdf && pdfBlobUrl && (
            <a
              href={pdfBlobUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs font-medium px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-zinc-700 transition-colors flex items-center gap-1.5 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
              title={t('common.openInNewTab')}
            >
              <ExternalLink className="w-3.5 h-3.5" />
              {t('common.openInNewTab')}
            </a>
          )}
          {showStatement ? (
            <ChevronUp className="w-5 h-5 text-zinc-400 dark:text-zinc-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-zinc-400 dark:text-zinc-400" />
          )}
        </div>
      </button>
      {showStatement && (
        contest.has_problem_statement_pdf ? (
          <div className="px-6 pb-6">
            {pdfLoading && !pdfBlobUrl ? (
              <div className="flex items-center justify-center h-96 bg-zinc-100 rounded-lg dark:bg-zinc-950/40">
                <div className="w-6 h-6 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : pdfBlobUrl ? (
              <iframe
                src={pdfBlobUrl}
                title={t('contest.problemStatement')}
                className="w-full rounded-lg border border-zinc-200 bg-white dark:border-zinc-800"
                style={{ height: '75vh', minHeight: 480 }}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-zinc-500 gap-3 dark:text-zinc-400">
                <AlertCircle className="w-8 h-8 text-amber-500 dark:text-amber-400" />
                <p>{t('contest.pdfLoadFailed')}</p>
                <button onClick={() => setPdfRetryCount((n) => n + 1)} className="btn-secondary text-sm">
                  {t('common.retry')}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="px-6 pb-6 prose prose-slate max-w-none dark:prose-invert dark:prose-violet">
            <ReactMarkdown>{contest.problem_statement || t('contest.noStatement')}</ReactMarkdown>
          </div>
        )
      )}
    </div>
  );
}
