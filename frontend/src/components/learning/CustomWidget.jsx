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

  // Common chrome injected into every widget iframe so DB-authored
  // widgets share the same look-and-feel as the built-in ``viz-sort``:
  // violet primary buttons, slate secondaries, consistent input
  // styling, dark-mode aware. Widgets only ship their content and use
  // these utility classes (``btn-primary``, ``btn-secondary``,
  // ``form-input``) for the chrome.
  const COMMON_STYLE = `
    html, body { margin: 0; padding: 0; height: 100%; box-sizing: border-box; }
    *, *::before, *::after { box-sizing: inherit; }
    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
           color: #0f172a; background: transparent; padding: 14px 16px; font-size: 13px; }

    .btn-primary, .btn-secondary {
      padding: 6px 12px; border: 0; border-radius: 8px; font-size: 13px;
      font-family: inherit; cursor: pointer; line-height: 1.2;
      transition: background-color 0.18s, color 0.18s, opacity 0.18s;
    }
    .btn-primary { background: #8b5cf6; color: #fff; }
    .btn-primary:hover:not(:disabled)   { background: #7c3aed; }
    .btn-secondary { background: #e2e8f0; color: #334155; }
    .btn-secondary:hover:not(:disabled) { background: #cbd5e1; }
    .btn-primary:disabled, .btn-secondary:disabled { opacity: 0.5; cursor: default; }

    .form-input, input[type="number"], input[type="text"] {
      padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 6px;
      background: #fff; color: #0f172a; font: inherit;
    }
    .form-input:focus, input[type="number"]:focus, input[type="text"]:focus {
      outline: 2px solid #c4b5fd; outline-offset: -1px;
    }

    .meta-row { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px;
                color: #64748b; margin-top: 8px; }
    .meta-row b { color: #0f172a; font-weight: 600; }
    .info-line { font-family: ui-monospace, "SF Mono", Menlo, monospace;
                 font-size: 12px; color: #7c3aed; min-height: 16px; }

    @media (prefers-color-scheme: dark) {
      body { color: #e2e8f0; }
      .btn-secondary { background: #334155; color: #e2e8f0; }
      .btn-secondary:hover:not(:disabled) { background: #475569; }
      .form-input, input[type="number"], input[type="text"] {
        background: #1e293b; border-color: #475569; color: #e2e8f0;
      }
      .meta-row { color: #94a3b8; }
      .meta-row b { color: #f1f5f9; }
      .info-line { color: #c4b5fd; }
    }
  `;

  // Build the iframe URL. We assemble the full HTML, then encode it as
  // a ``data:`` URI. ``encodeURIComponent`` handles non-ASCII (math
  // glyphs, accents) correctly without depending on ``btoa`` quirks.
  const dataUri = useMemo(() => {
    const html = [
      '<!DOCTYPE html>',
      '<html lang="fr"><head>',
      '<meta charset="utf-8" />',
      `<style>${COMMON_STYLE}</style>`,
      '</head><body>',
      // Inject params before the template so the user's <script> can read them.
      `<script>window.__params = ${paramsJson};</script>`,
      template,
      '</body></html>',
    ].join('\n');
    return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
  }, [template, paramsJson, COMMON_STYLE]);

  if (!template) {
    return (
      <div className="my-4 p-3 rounded-lg border border-amber-300 bg-amber-50 text-sm text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
        {t('learn.widget.customEmpty')}
      </div>
    );
  }

  const safeHeight = /^\d+(px|%)?$/.test(String(height)) ? height : '400';
  const heightCss = String(safeHeight).match(/(px|%)$/) ? safeHeight : `${safeHeight}px`;

  // Same outer chrome as the built-in ``SortViz`` (rounded-2xl border,
  // header with violet uppercase title) so the learning zone reads
  // visually consistent regardless of whether a widget is built-in or
  // DB-authored.
  return (
    <div className="my-6 not-prose rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-700/50 dark:bg-slate-900/50">
      {__title && (
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs uppercase tracking-wide font-semibold text-violet-600 dark:text-violet-400">
            {__title}
          </div>
        </div>
      )}
      <iframe
        title={__title || t('learn.widget.customIframeTitle')}
        src={dataUri}
        sandbox="allow-scripts"
        loading="lazy"
        className="w-full block rounded-lg"
        style={{ height: heightCss, border: 0, background: 'transparent' }}
      />
    </div>
  );
}
