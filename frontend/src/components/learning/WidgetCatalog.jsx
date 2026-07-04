import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Check, X, Sparkles } from 'lucide-react';
import { WIDGET_REGISTRY } from './widgets/registry';
import { loadWidgets, getCachedSync, subscribe } from './widgetsStore';

// Modal-style catalog of available learning widgets. Lives next to the
// admin editor; opens via a "Widgets disponibles" button. Each entry is
// rendered from the widget's own self-describing metadata in
// ``registry.js`` - adding a new widget there populates this catalog
// automatically with no extra UI work.
//
// ``onInsert(snippet)`` is the callback that splices the chosen
// widget's directive into the markdown editor.
export default function WidgetCatalog({ open, onClose, onInsert }) {
  const { t } = useTranslation();
  const [copiedKey, setCopiedKey] = useState(null);
  const [dbWidgets, setDbWidgets] = useState(() => getCachedSync() || []);

  useEffect(() => {
    let cancelled = false;
    loadWidgets().then((list) => { if (!cancelled) setDbWidgets(list); });
    const unsub = subscribe((list) => { if (!cancelled) setDbWidgets(list); });
    return () => { cancelled = true; unsub(); };
  }, []);

  if (!open) return null;

  // Merge registry: built-ins first, then DB widgets that aren't
  // shadowed. Each entry shape:
  //   { component? (built-in only), label, description, params,
  //     snippet, source: 'builtin' | 'custom' }
  const entries = [];
  for (const [name, entry] of Object.entries(WIDGET_REGISTRY)) {
    entries.push([name, { ...entry, source: 'builtin' }]);
  }
  const builtinNames = new Set(Object.keys(WIDGET_REGISTRY));
  for (const w of dbWidgets) {
    if (builtinNames.has(w.name)) continue;
    let params = [];
    let exampleAttrs = '';
    try {
      params = JSON.parse(w.params_schema || '[]') || [];
    } catch { /* ignore malformed */ }
    try {
      const obj = JSON.parse(w.example_params || '{}') || {};
      exampleAttrs = Object.entries(obj).map(([k, v]) => `${k}="${v}"`).join(' ');
    } catch { /* ignore malformed */ }
    entries.push([w.name, {
      label: w.title_fr || w.title_en || w.name,
      description: w.description_fr || w.description_en || '',
      params: params.map((p) => ({
        name: p.name || '',
        description: p.description || '',
        example: p.example || '',
      })),
      snippet: `:::${w.name}${exampleAttrs ? `{${exampleAttrs}}` : ''}\n:::`,
      source: 'custom',
    }]);
  }

  const handleCopy = async (key, snippet) => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 1500);
    } catch {
      /* clipboard might be denied - silently fail, user can still select manually */
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-zinc-200 dark:border-zinc-700/50">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent-500" />
            {t('learn.widget.catalog.title')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 dark:hover:bg-zinc-700/50 dark:text-zinc-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {t('learn.widget.catalog.intro')}
          </p>

          {entries.length === 0 && (
            <p className="text-sm text-zinc-400 dark:text-zinc-500">
              {t('learn.widget.catalog.empty')}
            </p>
          )}

          {entries.map(([key, entry]) => {
            // Built-in entries store i18n keys; custom entries store
            // already-translated strings. The ``source`` flag chooses.
            const label = entry.source === 'custom' ? entry.label : t(entry.label);
            const desc = entry.source === 'custom' ? entry.description : t(entry.description);
            return (
            <div
              key={key}
              className="border border-zinc-200 dark:border-zinc-700/50 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
                    {label}
                    {entry.source === 'custom' && (
                      <span className="text-[10px] uppercase tracking-wide bg-accent-100 dark:bg-accent-500/20 text-accent-700 dark:text-accent-300 px-1.5 py-0.5 rounded">
                        {t('learn.widget.catalog.customBadge')}
                      </span>
                    )}
                  </div>
                  <code className="text-xs text-accent-600 dark:text-accent-400">
                    :::{key}{'{...}'}
                  </code>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                    {desc}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => handleCopy(key, entry.snippet)}
                    className="px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-xs inline-flex items-center gap-1 dark:bg-zinc-700 dark:hover:bg-zinc-600 dark:text-zinc-200"
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
                    className="px-3 py-1.5 rounded-lg bg-accent-500 hover:bg-accent-600 text-white text-xs"
                  >
                    {t('learn.widget.catalog.insert')}
                  </button>
                </div>
              </div>

              {entry.params?.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wide font-semibold text-zinc-500 dark:text-zinc-400">
                    {t('learn.widget.catalog.parameters')}
                  </div>
                  <table className="w-full text-xs">
                    <tbody>
                      {entry.params.map((p) => (
                        <tr key={p.name} className="border-t border-zinc-100 dark:border-zinc-700/30">
                          <td className="py-1.5 pr-3 font-mono font-semibold text-accent-600 dark:text-accent-400 align-top w-24">
                            {p.name}
                          </td>
                          <td className="py-1.5 pr-3 text-zinc-600 dark:text-zinc-300">
                            {entry.source === 'custom' ? p.description : t(p.description)}
                          </td>
                          <td className="py-1.5 font-mono text-zinc-400 dark:text-zinc-500 align-top">
                            {p.example}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <pre className="bg-zinc-50 dark:bg-zinc-900 rounded-lg p-3 text-xs overflow-x-auto text-zinc-700 dark:text-zinc-300">
                <code>{entry.snippet}</code>
              </pre>
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
