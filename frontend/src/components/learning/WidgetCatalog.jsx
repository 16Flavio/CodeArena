import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Check, X, Sparkles } from 'lucide-react';
import { WIDGET_REGISTRY } from './widgets/registry';

// Modal-style catalog of available learning widgets. Lives next to the
// admin editor; opens via a "Widgets disponibles" button. Each entry is
// rendered from the widget's own self-describing metadata in
// ``registry.js`` — adding a new widget there populates this catalog
// automatically with no extra UI work.
//
// ``onInsert(snippet)`` is the callback that splices the chosen
// widget's directive into the markdown editor.
export default function WidgetCatalog({ open, onClose, onInsert }) {
  const { t } = useTranslation();
  const [copiedKey, setCopiedKey] = useState(null);

  if (!open) return null;

  const entries = Object.entries(WIDGET_REGISTRY);

  const handleCopy = async (key, snippet) => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 1500);
    } catch {
      /* clipboard might be denied — silently fail, user can still select manually */
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="glass-card max-w-3xl w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-slate-700/50">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-violet-500" />
            {t('learn.widget.catalog.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-600 dark:hover:bg-slate-700/50 dark:text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-slate-500 dark:text-gray-400">
            {t('learn.widget.catalog.intro')}
          </p>

          {entries.length === 0 && (
            <p className="text-sm text-slate-400 dark:text-gray-500">
              {t('learn.widget.catalog.empty')}
            </p>
          )}

          {entries.map(([key, entry]) => (
            <div
              key={key}
              className="border border-gray-200 dark:border-slate-700/50 rounded-xl p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="font-semibold text-slate-900 dark:text-white">
                    {t(entry.label)}
                  </div>
                  <code className="text-xs text-violet-600 dark:text-violet-400">
                    :::{key}{'{...}'}
                  </code>
                  <p className="text-sm text-slate-500 dark:text-gray-400 mt-1">
                    {t(entry.description)}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => handleCopy(key, entry.snippet)}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs inline-flex items-center gap-1 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-gray-200"
                  >
                    {copiedKey === key ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        {t('learn.widget.catalog.copied')}
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        {t('learn.widget.catalog.copy')}
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => { onInsert(entry.snippet); onClose(); }}
                    className="px-3 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-xs"
                  >
                    {t('learn.widget.catalog.insert')}
                  </button>
                </div>
              </div>

              {entry.params?.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400">
                    {t('learn.widget.catalog.parameters')}
                  </div>
                  <table className="w-full text-xs">
                    <tbody>
                      {entry.params.map((p) => (
                        <tr key={p.name} className="border-t border-gray-100 dark:border-slate-700/30">
                          <td className="py-1.5 pr-3 font-mono font-semibold text-violet-600 dark:text-violet-400 align-top w-24">
                            {p.name}
                          </td>
                          <td className="py-1.5 pr-3 text-slate-600 dark:text-gray-300">
                            {t(p.description)}
                          </td>
                          <td className="py-1.5 font-mono text-slate-400 dark:text-gray-500 align-top">
                            {p.example}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <pre className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-xs overflow-x-auto text-slate-700 dark:text-gray-300">
                <code>{entry.snippet}</code>
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
