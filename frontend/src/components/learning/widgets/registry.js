import SortViz from './SortViz';
import HtmlEmbed from './HtmlEmbed';

/**
 * Registry of all available widgets, with self-describing metadata.
 *
 * The same registry is consumed by:
 *
 * - the markdown renderer (LessonMarkdown.jsx) — to map directive
 *   names to React components,
 * - the admin editor's widget catalog modal — to list what's
 *   available, with the directive syntax + a copy-pasteable example.
 *
 * Adding a new widget = adding a new entry here. Each entry MUST
 * include:
 *
 * - ``component``: the React component to render
 * - ``label``: short human-readable name (FR/EN keys)
 * - ``description``: 1-2 sentences (FR/EN keys)
 * - ``params``: ordered array of {name, description, example} —
 *   shown in the catalog as a small attribute reference
 * - ``snippet``: a ready-to-paste directive string
 *
 * The label / description fields point at i18n keys so they're
 * translated. Keys live under ``learn.widget.catalog.*`` in fr.json /
 * en.json.
 */
export const WIDGET_REGISTRY = {
  'viz-sort': {
    component: SortViz,
    label: 'learn.widget.catalog.sortLabel',
    description: 'learn.widget.catalog.sortDescription',
    params: [
      {
        name: 'algo',
        description: 'learn.widget.catalog.sortParamAlgo',
        example: 'bubble | insertion | selection',
      },
      {
        name: 'data',
        description: 'learn.widget.catalog.sortParamData',
        example: '[5,2,8,1,9,3]',
      },
    ],
    snippet: ':::viz-sort{algo="bubble" data="[5,2,8,1,9,3]"}\n:::',
  },
  'widget-html': {
    component: HtmlEmbed,
    label: 'learn.widget.catalog.htmlLabel',
    description: 'learn.widget.catalog.htmlDescription',
    params: [
      {
        name: 'src',
        description: 'learn.widget.catalog.htmlParamSrc',
        example: '/api/learning/assets/12/3-anim.html',
      },
      {
        name: 'height',
        description: 'learn.widget.catalog.htmlParamHeight',
        example: '400',
      },
      {
        name: 'title',
        description: 'learn.widget.catalog.htmlParamTitle',
        example: 'BST animation',
      },
    ],
    snippet: ':::widget-html{src="/api/learning/assets/<lesson_id>/<asset_id>-fichier.html" height="400" title="Mon animation"}\n:::',
  },
};
