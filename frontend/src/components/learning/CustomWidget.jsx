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
 *     URLs load with their own (empty) policy - the parent CSP does
 *     not transfer - so widget scripts can run. The sandbox attribute
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
  // a viz "stage" up top, a centered ``.controls`` row of icon buttons
  // below (accent primary for play/run, neutral secondary for
  // step/reset/pause), with dark-mode-aware tokens. Widgets only ship
  // their stage HTML and the icon button shells; ``window.__svg(name)``
  // returns the inline SVG markup for the standard Lucide icons used
  // throughout (play, pause, step, reset, plus, minus).
  const COMMON_STYLE = `
    html, body { margin: 0; padding: 0; height: 100%; box-sizing: border-box; }
    *, *::before, *::after { box-sizing: inherit; }
    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
           color: #18181b; background: transparent; padding: 14px 16px; font-size: 13px; }

    .stage { width: 100%; }

    .controls {
      display: flex; align-items: center; justify-content: center;
      gap: 8px; margin-top: 14px; flex-wrap: wrap;
    }
    .controls > .group { display: inline-flex; align-items: center; gap: 6px; }

    .btn-icon, .btn-icon-primary, .btn-icon-secondary {
      display: inline-flex; align-items: center; justify-content: center;
      width: 32px; height: 32px; padding: 0; border: 0; border-radius: 8px;
      cursor: pointer; line-height: 1;
      transition: background-color 0.18s, color 0.18s, opacity 0.18s;
    }
    .btn-icon-primary   { background: #3a6690; color: #fff; }
    .btn-icon-primary:hover:not(:disabled)   { background: #325575; }
    .btn-icon-secondary { background: #e4e4e7; color: #3f3f46; }
    .btn-icon-secondary:hover:not(:disabled) { background: #d4d4d8; }
    .btn-icon-primary:disabled, .btn-icon-secondary:disabled { opacity: 0.5; cursor: default; }
    .btn-icon-primary svg, .btn-icon-secondary svg { width: 16px; height: 16px; display: block; }

    .form-input, input[type="number"], input[type="text"], input[type="range"] {
      padding: 5px 8px; border: 1px solid #d4d4d8; border-radius: 6px;
      background: #fff; color: #18181b; font: inherit; height: 32px;
    }
    input[type="range"] { padding: 0; min-width: 110px; height: 32px; background: transparent; border: 0; }
    .form-input:focus, input[type="number"]:focus, input[type="text"]:focus {
      outline: 2px solid #9cbbd6; outline-offset: -1px;
    }
    label.field { display: inline-flex; align-items: center; gap: 6px;
                  font-size: 12px; color: #52525b; }
    label.field input[type="number"], label.field input[type="text"] { width: 80px; }

    .meta-row { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px;
                color: #71717a; margin-top: 10px; justify-content: center; }
    .meta-row b { color: #18181b; font-weight: 600; }
    .info-line { font-family: ui-monospace, "SF Mono", Menlo, monospace;
                 font-size: 12px; color: #325575; min-height: 16px;
                 text-align: center; margin-top: 10px; }

    @media (prefers-color-scheme: dark) {
      body { color: #e4e4e7; }
      .btn-icon-secondary { background: #3f3f46; color: #e4e4e7; }
      .btn-icon-secondary:hover:not(:disabled) { background: #52525b; }
      .form-input, input[type="number"], input[type="text"] {
        background: #27272a; border-color: #52525b; color: #e4e4e7;
      }
      label.field { color: #a1a1aa; }
      .meta-row { color: #a1a1aa; }
      .meta-row b { color: #e4e4e7; }
      .info-line { color: #9cbbd6; }
    }
  `;

  // Inline Lucide-style icons. We expose them via ``window.__svg(name)``
  // so widget templates can drop them into icon buttons without
  // duplicating the path data. Same icons SortViz uses
  // (play / pause / step (chevrons-right) / reset (rotate-ccw)).
  const ICON_HELPER = `
    window.__icons = {
      play:   '<polygon points="6 3 20 12 6 21 6 3"/>',
      pause:  '<rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/>',
      step:   '<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>',
      reset:  '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
      plus:   '<path d="M5 12h14"/><path d="M12 5v14"/>',
      minus:  '<path d="M5 12h14"/>',
      load:   '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>'
    };
    window.__svg = function (name) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        + (window.__icons[name] || '') + '</svg>';
    };
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
      `<script>${ICON_HELPER}</script>`,
      '</head><body>',
      // Inject params before the template so the user's <script> can read them.
      `<script>window.__params = ${paramsJson};</script>`,
      template,
      '</body></html>',
    ].join('\n');
    return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
  }, [template, paramsJson, COMMON_STYLE, ICON_HELPER]);

  if (!template) {
    return (
      <div className="my-4 p-3 rounded-lg border border-amber-300 bg-amber-50 text-sm text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
        {t('learn.widget.customEmpty')}
      </div>
    );
  }

  const safeHeight = /^\d+(px|%)?$/.test(String(height)) ? height : '400';
  const heightCss = String(safeHeight).match(/(px|%)$/) ? safeHeight : `${safeHeight}px`;

  // Same outer chrome as the built-in ``SortViz`` (rounded-lg border,
  // header with accent uppercase title) so the learning zone reads
  // visually consistent regardless of whether a widget is built-in or
  // DB-authored.
  return (
    <div className="my-6 not-prose rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700/50 dark:bg-zinc-900/50">
      {__title && (
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs uppercase tracking-wide font-semibold text-accent-600 dark:text-accent-400">
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
