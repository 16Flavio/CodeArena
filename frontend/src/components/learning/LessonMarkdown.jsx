import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkDirective from 'remark-directive';
import { visit } from 'unist-util-visit';
import { WIDGET_REGISTRY } from './widgets/registry';
import CustomWidget from './CustomWidget';
import { loadWidgets, getCachedSync, subscribe } from './widgetsStore';

// Two layers of widgets:
//   1. Built-in (WIDGET_REGISTRY) — React components like SortViz.
//      Polished, integrated theme, hand-written. Cannot be edited
//      from the UI.
//   2. Custom (DB-backed via widgetsStore) — admin-authored HTML+JS
//      bodies rendered in a sandboxed iframe via ``CustomWidget``.
//      Editable from the admin UI, isolated by the iframe sandbox.
//
// Lesson markdown's directive name is matched against both. Built-in
// wins on conflict (an admin can't accidentally shadow a polished
// widget by creating one with the same name — the create endpoint
// validates uniqueness in DB but not against built-ins; the renderer
// simply prefers the built-in).
//
// Directive syntax (standard remark-directive container form):
//
//   :::viz-sort{algo="bubble" data="[5,2,8,1]"}
//   :::

function buildPlugin(knownDirectives) {
  return function remarkLearningWidgets() {
    return (tree) => {
      visit(tree, (node) => {
        if (
          node.type === 'containerDirective' ||
          node.type === 'leafDirective' ||
          node.type === 'textDirective'
        ) {
          if (!knownDirectives.has(node.name)) {
            // Unknown directive — render as plain text so authors see
            // their typo rather than silently dropping content.
            return;
          }
          const data = node.data ?? (node.data = {});
          // Use a custom tag name so we can target it in the
          // ``components`` prop. The leading ``learning-`` prefix avoids
          // colliding with native HTML elements.
          data.hName = `learning-${node.name}`;
          data.hProperties = { ...(node.attributes ?? {}) };
        }
      });
    };
  };
}

/**
 * Render a lesson markdown body. Custom widgets are interpolated via
 * remark directives — see ``WIDGETS`` for the static registry and the
 * widgetsStore for DB-backed widgets.
 *
 * Tailwind ``prose`` classes give pleasant typography for free; the
 * widget components opt out via ``not-prose``.
 */
export default function LessonMarkdown({ children }) {
  // Hydrate the DB widget list once at mount and subscribe to changes
  // so an admin save updates open lesson previews live.
  const [dbWidgets, setDbWidgets] = useState(() => getCachedSync() || []);

  useEffect(() => {
    let cancelled = false;
    loadWidgets().then((list) => {
      if (!cancelled) setDbWidgets(list);
    });
    const unsubscribe = subscribe((list) => {
      if (!cancelled) setDbWidgets(list);
    });
    return () => { cancelled = true; unsubscribe(); };
  }, []);

  const dbByName = useMemo(() => {
    const out = {};
    for (const w of dbWidgets) out[w.name] = w;
    return out;
  }, [dbWidgets]);

  // Set of every directive name we know how to render. Built-ins
  // shadow DB widgets if names collide.
  const knownDirectives = useMemo(() => {
    const s = new Set(Object.keys(dbByName));
    for (const k of Object.keys(WIDGET_REGISTRY)) s.add(k);
    return s;
  }, [dbByName]);

  // Map directive tag → React component instance. Has to be rebuilt
  // whenever the DB widget list changes (otherwise newly-created
  // widgets render as plain HTML).
  const widgetComponents = useMemo(() => {
    const out = {};
    // Built-in first.
    for (const [name, entry] of Object.entries(WIDGET_REGISTRY)) {
      const Component = entry.component;
      out[`learning-${name}`] = (props) => <Component {...props} />;
    }
    // DB-backed (only kicks in if not already taken by a built-in
    // with the same name — Object.assign order matters).
    for (const w of dbWidgets) {
      const tag = `learning-${w.name}`;
      if (out[tag]) continue;  // built-in wins
      out[tag] = (props) => (
        <CustomWidget
          template={w.html_template}
          __title={w.title_fr || w.title_en || w.name}
          {...props}
        />
      );
    }
    return out;
  }, [dbWidgets]);

  const remarkPlugins = useMemo(
    () => [remarkGfm, remarkDirective, buildPlugin(knownDirectives)],
    [knownDirectives],
  );

  return (
    <div className="prose prose-slate max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        components={widgetComponents}
      >
        {children || ''}
      </ReactMarkdown>
    </div>
  );
}
