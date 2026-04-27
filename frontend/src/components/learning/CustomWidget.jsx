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
 *   - We serve the iframe via a ``data:text/html`` URL rather than
 *     ``srcdoc``. Why: ``srcdoc`` inherits the parent's CSP, and our
 *     parent forbids inline scripts (``script-src 'self'``), which
 *     would block every ``<script>`` inside the widget. ``data:``
 *     URLs load with their own (empty) policy — the parent CSP does
 *     not transfer — so widget scripts can run. The sandbox attribute
 *     keeps the iframe in an opaque origin regardless.
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
  // would also serialize. We strip react-markdown internals (``node``,
  // ``children``) before serialising so the iframe gets only the
  // user-visible props from the directive.
  const paramsJson = useMemo(() => {
    const clean = {};
    for (const [k, v] of Object.entries(params)) {
      if (k === 'node' || k === 'children') continue;
      const t = typeof v;
      if (t === 'string' || t === 'number' || t === 'boolean' || v == null) {
        clean[k] = v;
      }
    }
    try { return JSON.stringify(clean); }
    catch { return '{}'; }
  }, [params]);

  // Build the iframe URL. We assemble the full HTML, then encode it as
  // a ``data:`` URI. ``encodeURIComponent`` handles non-ASCII (math
  // glyphs, accents) correctly without depending on ``btoa`` quirks.
  const dataUri = useMemo(() => {
    const html = [
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
    return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
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
        src={dataUri}
        sandbox="allow-scripts"
        loading="lazy"
        className="w-full block"
        style={{ height: heightCss, border: 0 }}
      />
    </div>
  );
}
