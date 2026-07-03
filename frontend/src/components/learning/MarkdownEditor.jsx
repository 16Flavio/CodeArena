import { useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import CodeMirror from '@uiw/react-codemirror';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';
import { EditorView, keymap } from '@codemirror/view';
import {
  Bold, Italic, Heading1, Heading2, Heading3, List, ListOrdered,
  Link as LinkIcon, Image as ImageIcon, Code as CodeIcon,
  FileCode2, Sigma, Sparkles, Code2,
} from 'lucide-react';
import { useTheme } from '../../ThemeContext';

// Wrap the current selection with prefix/suffix, or insert prefix
// at cursor when nothing is selected. The optional ``placeholder`` is
// inserted (and selected) inside an empty wrap so the caret lands on
// useful text rather than between two delimiters.
function applyWrap(view, prefix, suffix = prefix, placeholder = '') {
  if (!view) return;
  const { from, to } = view.state.selection.main;
  const selected = view.state.doc.sliceString(from, to);
  const inner = selected || placeholder;
  const insert = prefix + inner + suffix;
  view.dispatch({
    changes: { from, to, insert },
    selection: selected
      ? { anchor: from, head: from + insert.length }
      : { anchor: from + prefix.length, head: from + prefix.length + inner.length },
  });
  view.focus();
}

// Prefix every line in the current selection (or the line under the
// cursor) with the given string. Useful for headings, lists, blockquotes.
function applyLinePrefix(view, prefix) {
  if (!view) return;
  const { from, to } = view.state.selection.main;
  const startLine = view.state.doc.lineAt(from);
  const endLine = view.state.doc.lineAt(to);
  const changes = [];
  for (let n = startLine.number; n <= endLine.number; n++) {
    const line = view.state.doc.line(n);
    // Don't double-prefix lines that already have it.
    if (!line.text.startsWith(prefix)) {
      changes.push({ from: line.from, insert: prefix });
    }
  }
  if (changes.length) {
    view.dispatch({ changes });
  }
  view.focus();
}


// Top-level so the new ``react-hooks/static-components`` rule
// doesn't flag in-render component creation.
function ToolbarButton({ onClick, title, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className="p-1.5 rounded hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900 dark:hover:bg-zinc-700/50 dark:text-zinc-300 dark:hover:text-white"
    >
      {children}
    </button>
  );
}

function insertAtCursor(view, text) {
  if (!view) return;
  const { from, to } = view.state.selection.main;
  view.dispatch({
    changes: { from, to, insert: text },
    selection: { anchor: from + text.length },
  });
  view.focus();
}

/**
 * CodeMirror-backed markdown editor with a formatting toolbar.
 *
 * Props:
 *   value, onChange       — controlled string state
 *   onUploadImage(file)   — optional async; should return the markdown
 *                           snippet to insert (e.g. ``![name](url)``)
 *   onPickWidget()        — optional; opens the widget catalog modal
 *   onPickExercise()      — optional; opens the exercise picker modal
 *
 * Drag-and-drop image upload is wired when ``onUploadImage`` is set.
 * Keyboard shortcuts: Ctrl/Cmd+B (bold), Ctrl/Cmd+I (italic),
 * Ctrl/Cmd+K (link).
 */
export default function MarkdownEditor({
  value, onChange,
  onUploadImage, onPickWidget, onPickExercise,
  height = '70vh',
}) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const viewRef = useRef(null);

  const onCmCreate = useCallback((view) => {
    viewRef.current = view;
  }, []);

  const handleImageButton = async () => {
    if (!onUploadImage) return;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const snippet = await onUploadImage(file);
      if (snippet) insertAtCursor(viewRef.current, '\n' + snippet + '\n');
    };
    input.click();
  };

  const handleLink = () => {
    const url = window.prompt(t('mdEditor.linkPrompt'), 'https://');
    if (!url) return;
    applyWrap(viewRef.current, '[', `](${url})`, t('mdEditor.linkText'));
  };

  // Drop handler: image file drops are uploaded; everything else is
  // ignored so CodeMirror's default text-drop behaviour kicks in.
  const handleDrop = useCallback(async (e) => {
    if (!onUploadImage) return;
    const files = Array.from(e.dataTransfer?.files || []);
    const images = files.filter((f) => f.type.startsWith('image/'));
    if (!images.length) return;
    e.preventDefault();
    for (const file of images) {
      const snippet = await onUploadImage(file);
      if (snippet) insertAtCursor(viewRef.current, '\n' + snippet + '\n');
    }
  }, [onUploadImage]);

  // The keymap below adds 3 shortcuts on top of CodeMirror's default
  // markdown-aware bindings (autocomplete, indent, history).
  const cmExtensions = [
    markdown(),
    EditorView.lineWrapping,
    keymap.of([
      {
        key: 'Mod-b',
        run: (v) => { applyWrap(v, '**', '**', t('mdEditor.boldPlaceholder')); return true; },
      },
      {
        key: 'Mod-i',
        run: (v) => { applyWrap(v, '*', '*', t('mdEditor.italicPlaceholder')); return true; },
      },
      {
        key: 'Mod-k',
        run: () => { handleLink(); return true; },
      },
    ]),
  ];

  return (
    <div
      className="border border-zinc-200 rounded-lg overflow-hidden bg-white dark:bg-zinc-900 dark:border-zinc-700/50"
      onDrop={handleDrop}
      onDragOver={(e) => onUploadImage && e.preventDefault()}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 flex-wrap px-2 py-1.5 border-b border-zinc-200 dark:border-zinc-700/50 bg-zinc-50 dark:bg-zinc-800/40">
        <ToolbarButton title={t('mdEditor.bold') + ' (Ctrl+B)'} onClick={() => applyWrap(viewRef.current, '**', '**', t('mdEditor.boldPlaceholder'))}>
          <Bold className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title={t('mdEditor.italic') + ' (Ctrl+I)'} onClick={() => applyWrap(viewRef.current, '*', '*', t('mdEditor.italicPlaceholder'))}>
          <Italic className="w-4 h-4" />
        </ToolbarButton>
        <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-1" />
        <ToolbarButton title="H1" onClick={() => applyLinePrefix(viewRef.current, '# ')}>
          <Heading1 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title="H2" onClick={() => applyLinePrefix(viewRef.current, '## ')}>
          <Heading2 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title="H3" onClick={() => applyLinePrefix(viewRef.current, '### ')}>
          <Heading3 className="w-4 h-4" />
        </ToolbarButton>
        <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-1" />
        <ToolbarButton title={t('mdEditor.list')} onClick={() => applyLinePrefix(viewRef.current, '- ')}>
          <List className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title={t('mdEditor.orderedList')} onClick={() => applyLinePrefix(viewRef.current, '1. ')}>
          <ListOrdered className="w-4 h-4" />
        </ToolbarButton>
        <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-1" />
        <ToolbarButton title={t('mdEditor.link') + ' (Ctrl+K)'} onClick={handleLink}>
          <LinkIcon className="w-4 h-4" />
        </ToolbarButton>
        {onUploadImage && (
          <ToolbarButton title={t('mdEditor.image')} onClick={handleImageButton}>
            <ImageIcon className="w-4 h-4" />
          </ToolbarButton>
        )}
        <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-1" />
        <ToolbarButton title={t('mdEditor.codeInline')} onClick={() => applyWrap(viewRef.current, '`', '`', 'code')}>
          <CodeIcon className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title={t('mdEditor.codeBlock')} onClick={() => applyWrap(viewRef.current, '```\n', '\n```', 'code')}>
          <FileCode2 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton title={t('mdEditor.math')} onClick={() => applyWrap(viewRef.current, '$$', '$$', '\\frac{1}{2}')}>
          <Sigma className="w-4 h-4" />
        </ToolbarButton>
        <span className="w-px h-5 bg-zinc-200 dark:bg-zinc-700 mx-1" />
        {onPickExercise && (
          <ToolbarButton title={t('mdEditor.exercise')} onClick={onPickExercise}>
            <Code2 className="w-4 h-4" />
          </ToolbarButton>
        )}
        {onPickWidget && (
          <ToolbarButton title={t('mdEditor.widget')} onClick={onPickWidget}>
            <Sparkles className="w-4 h-4" />
          </ToolbarButton>
        )}
        {onUploadImage && (
          <span className="ml-auto text-[11px] text-zinc-400 dark:text-zinc-500 px-2">
            {t('mdEditor.dndHint')}
          </span>
        )}
      </div>

      {/* Editor — switches to oneDark when the app is in dark mode so
          the white-on-light-grey contrast issue goes away. */}
      <CodeMirror
        value={value}
        onChange={onChange}
        onCreateEditor={onCmCreate}
        extensions={cmExtensions}
        theme={theme === 'dark' ? oneDark : 'light'}
        height={height}
        basicSetup={{
          lineNumbers: false,
          foldGutter: false,
          highlightActiveLine: true,
          indentOnInput: true,
          tabSize: 2,
          autocompletion: true,
        }}
      />
    </div>
  );
}
