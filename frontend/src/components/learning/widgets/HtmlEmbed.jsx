import { useTranslation } from 'react-i18next';

/**
 * `:::widget-html{src="/api/learning/assets/<lesson_id>/<asset_id>-foo.html" height="400"}`
 *
 * Embeds an arbitrary HTML/JS file the admin uploaded. The iframe is
 * sandboxed — ``allow-scripts`` only, NO ``allow-same-origin``,
 * ``allow-forms``, ``allow-popups``, ``allow-modals`` — so the embedded
 * page can run JavaScript inside its own isolated context but cannot:
 *
 * - read the parent's localStorage (where the JWT lives),
 * - read the parent's cookies,
 * - submit forms or open windows pointing at our origin,
 * - escape into the main DOM via top-level navigation.
 *
 * That makes "the admin uploads a custom HTML widget" a safe operation
 * even on a public deployment: the upload is gated to admin already,
 * but even a malicious admin's page is sandboxed away from the user's
 * session.
 *
 * Falls back to an inline error block if ``src`` is missing — typical
 * cause is a typo in the directive's attributes.
 */
export default function HtmlEmbed({ src, height = '400', title = '' }) {
  const { t } = useTranslation();
  if (!src || typeof src !== 'string' || !src.startsWith('/api/learning/assets/')) {
    return (
      <div className="my-4 p-3 rounded-lg border border-red-300 bg-red-50 text-sm text-red-700 dark:bg-red-950/30 dark:border-red-800 dark:text-red-300">
        {t('learn.widget.htmlInvalid')}
      </div>
    );
  }
  const safeHeight = /^\d+(px|%)?$/.test(height) ? height : '400';
  return (
    <div className="my-6 not-prose rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-sm dark:border-slate-700/50 dark:bg-slate-900/50">
      <iframe
        src={src}
        title={title || t('learn.widget.htmlIframeTitle')}
        sandbox="allow-scripts"
        loading="lazy"
        className="w-full block"
        style={{ height: safeHeight.endsWith('px') || safeHeight.endsWith('%') ? safeHeight : `${safeHeight}px`, border: 0 }}
      />
    </div>
  );
}
