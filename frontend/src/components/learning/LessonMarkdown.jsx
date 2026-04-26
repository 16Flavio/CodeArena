import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkDirective from 'remark-directive';
import { visit } from 'unist-util-visit';
import { WIDGET_REGISTRY } from './widgets/registry';

// Widget registry lives in ./widgets/registry.js and is shared with
// the admin catalog UI (so adding a widget there documents itself).
//
// The directive syntax is the standard remark-directive container form:
//
//   :::viz-sort{algo="bubble" data="[5,2,8,1]"}
//   :::
//
// Inline form ``::viz-sort{...}`` and leaf form ``:::viz-sort{...}``
// without a closing fence both work — we accept all three.

/**
 * remark plugin: rewrite directive nodes into a custom HTML-like node
 * with a ``data-widget`` attribute. ReactMarkdown then matches the
 * tag in the components map below and instantiates the React widget.
 *
 * We do NOT pass the args as innerText; we encode them as data-*
 * attributes so the widget receives them as props.
 */
function remarkLearningWidgets() {
  return (tree) => {
    visit(tree, (node) => {
      if (
        node.type === 'containerDirective' ||
        node.type === 'leafDirective' ||
        node.type === 'textDirective'
      ) {
        if (!Object.prototype.hasOwnProperty.call(WIDGET_REGISTRY, node.name)) {
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
}

// Map the custom tag names back to React widgets. Each widget receives
// the directive's attributes as props. Whatever the directive author
// wrote in ``key="value"`` arrives here as ``props.key === "value"``.
const widgetComponents = Object.fromEntries(
  Object.entries(WIDGET_REGISTRY).map(([name, entry]) => {
    const Component = entry.component;
    return [
      `learning-${name}`,
      (props) => <Component {...props} />,
    ];
  }),
);

const REMARK_PLUGINS = [remarkGfm, remarkDirective, remarkLearningWidgets];

/**
 * Render a lesson markdown body. Custom widgets are interpolated via
 * remark directives — see ``WIDGETS`` for the registry.
 *
 * Tailwind ``prose`` classes give pleasant typography for free; the
 * widget components opt out via ``not-prose``.
 */
export default function LessonMarkdown({ children }) {
  return (
    <div className="prose prose-slate max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        components={widgetComponents}
      >
        {children || ''}
      </ReactMarkdown>
    </div>
  );
}
