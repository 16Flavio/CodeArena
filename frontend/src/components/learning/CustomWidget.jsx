import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Renders an admin-authored widget (stored in DB as ``html_template``)
 * inside a sandboxed iframe.
 *
 * Security:
 *   - ``sandbox="allow-scripts"`` only. NO ``allow-same-origin``,
 *     ``allow-forms``, ``allow-popups``, ``allow-modals``.
 *   - With no allow-same-origin the iframe runs in an opaque origin.
 *     It cannot read the parent's localStorage / cookies, so even
 *     wildly malicious widget code cannot lift the JWT.
 *   - The iframe's source comes from ``srcdoc`` (an inline string)
 *     rather than a remote URL — no extra round-trip, no path-
 *     traversal surface, no caching.
 *
 * Params injection: the directive's attributes (``algo="bubble"`` …)
 * land here as React props. We serialize them to JSON and surface
 * them via ``window.__params`` inside the iframe before the user's
 * template runs. The template can read ``window.__params.algo`` etc.
 */
export default function CustomWidget({ template = '', height = '400', __title = '', ...params }) {
  const { t } = useTranslation();

  // JSON-serialise the directive attrs. Strings / numbers / arrays
  // are fine; nested objects are unusual in directive attrs but
  // would also serialize.
  const paramsJson = useMemo(() => JSON.stringify(params), [params]);

  // Build the srcdoc. The template body is inserted verbatim — admin
  // is trusted (the writes are admin-gated in the backend) and the
  // sandbox isolates abuses.
  const srcdoc = useMemo(() => {
    return [
      '<!DOCTYPE html>',
      '<html lang="fr"><head>',
      '<meta charset="utf-8" />',
      '<style>',
      '  html, body { margin: 0; padding: 0; height: 100%; box-sizing: border-box; }',
      '  *, *::before, *::after { box-sizing: inherit; }',
      '  body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;',
      '         color: #0f172a; background: transparent; padding: 12px; }',
      '  @media (prefers-color-scheme: dark) { body { color: #e2e8f0; } }',
      '</style>',
      '</head><body>',
      // Inject params before the template so the user's <script> can read them.
      `<script>window.__params = ${paramsJson};</script>`,
      template,
      '</body></html>',
    ].join('\n');
  }, [template, paramsJson]);

  if (!template) {
    return (
      <div className="my-4 p-3 rounded-lg border border-amber-300 bg-amber-50 text-sm text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
        {t('learn.widget.customEmpty')}
      </div>
    );
  }

  const safeHeight = /^\d+(px|%)?$/.test(String(height)) ? height : '400';
  const heightCss = String(safeHeight).match(/(px|%)$/) ? safeHeight : `${safeHeight}px`;

  return (
    <div className="my-6 not-prose rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-sm dark:border-slate-700/50 dark:bg-slate-900/50">
      <iframe
        title={__title || t('learn.widget.customIframeTitle')}
        srcDoc={srcdoc}
        sandbox="allow-scripts"
        loading="lazy"
        className="w-full block"
        style={{ height: heightCss, border: 0 }}
      />
    </div>
  );
}
