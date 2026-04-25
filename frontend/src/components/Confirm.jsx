import {
  createContext, useCallback, useContext, useEffect, useRef, useState,
} from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, X } from 'lucide-react';

// Promise-based replacement for the browser's blocking ``confirm()`` /
// ``prompt()``. Both are inaccessible (no focus trap, untranslatable
// labels, system-styled), so we mount a single styled modal at the
// root and expose two hooks:
//
//   const confirm = useConfirm();
//   const ok = await confirm({ title, message, danger });
//
//   const prompt = usePrompt();
//   const value = await prompt({ title, message, defaultValue });
//
// ``confirm`` resolves ``true`` / ``false``. ``prompt`` resolves the
// string the user typed, or ``null`` if cancelled.
//
// Both honour ESC and click-outside as cancel, and submit on Enter
// (confirm: confirm, prompt: confirm if non-empty).

const DialogContext = createContext(null);

export function ConfirmProvider({ children }) {
  // Single dialog state — only one prompt/confirm can be open at a time,
  // matching the native browser semantics callers are migrating from.
  const [dialog, setDialog] = useState(null);
  const resolveRef = useRef(null);

  const closeWith = useCallback((value) => {
    const resolve = resolveRef.current;
    resolveRef.current = null;
    setDialog(null);
    if (resolve) resolve(value);
  }, []);

  const confirm = useCallback((opts = {}) => new Promise((resolve) => {
    resolveRef.current = resolve;
    setDialog({ kind: 'confirm', ...opts });
  }), []);

  const prompt = useCallback((opts = {}) => new Promise((resolve) => {
    resolveRef.current = resolve;
    setDialog({ kind: 'prompt', ...opts });
  }), []);

  return (
    <DialogContext.Provider value={{ confirm, prompt }}>
      {children}
      {dialog && createPortal(
        <DialogShell dialog={dialog} closeWith={closeWith} />,
        document.body,
      )}
    </DialogContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useConfirm() {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error('useConfirm must be used inside <ConfirmProvider>');
  return ctx.confirm;
}

// eslint-disable-next-line react-refresh/only-export-components
export function usePrompt() {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error('usePrompt must be used inside <ConfirmProvider>');
  return ctx.prompt;
}

function DialogShell({ dialog, closeWith }) {
  const { t } = useTranslation();
  const isPrompt = dialog.kind === 'prompt';
  // The component is freshly mounted each time the parent opens a
  // new dialog, so the lazy initializer is enough — no separate reset
  // effect needed.
  const [value, setValue] = useState(dialog.defaultValue ?? '');
  const dialogRef = useRef(null);
  const inputRef = useRef(null);
  const confirmBtnRef = useRef(null);

  // Focus the right element on open + autofocus inside the dialog so
  // ESC/Enter route to it without a tab trip.
  useEffect(() => {
    const target = isPrompt ? inputRef.current : confirmBtnRef.current;
    target?.focus?.();
    if (isPrompt && inputRef.current) {
      inputRef.current.select?.();
    }
  }, [isPrompt]);

  // Global key handlers — ESC cancels, Enter confirms (when not in
  // a multi-line input).
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeWith(isPrompt ? null : false);
      } else if (e.key === 'Enter') {
        // For prompts, Enter should submit unless the user is editing
        // a multi-line field (we don't render one, but keep the guard).
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag !== 'textarea') {
          e.preventDefault();
          if (isPrompt) closeWith(value);
          else closeWith(true);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closeWith, isPrompt, value]);

  const onBackdropClick = (e) => {
    if (e.target === dialogRef.current) {
      closeWith(isPrompt ? null : false);
    }
  };

  const danger = !!dialog.danger;
  const title = dialog.title || (danger ? t('confirm.dangerTitle') : t('confirm.title'));
  const message = dialog.message || '';
  const confirmLabel = dialog.confirmLabel
    || (isPrompt ? t('confirm.ok') : danger ? t('confirm.confirmDanger') : t('confirm.confirm'));
  const cancelLabel = dialog.cancelLabel || t('confirm.cancel');

  return (
    <div
      ref={dialogRef}
      onClick={onBackdropClick}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 backdrop-blur-sm animate-fade-in p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div
        className="glass-card max-w-md w-full p-6 space-y-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h2
            id="dialog-title"
            className={`text-lg font-bold flex items-center gap-2 ${
              danger ? 'text-red-700 dark:text-red-300' : 'text-slate-900 dark:text-white'
            }`}
          >
            {danger && <AlertTriangle className="w-5 h-5 flex-shrink-0" />}
            {title}
          </h2>
          <button
            type="button"
            onClick={() => closeWith(isPrompt ? null : false)}
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-gray-200"
            aria-label={cancelLabel}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {message && (
          <p className="text-sm text-slate-700 dark:text-gray-300 whitespace-pre-wrap">
            {message}
          </p>
        )}

        {isPrompt && (
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={dialog.placeholder || ''}
            className="input-field"
          />
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => closeWith(isPrompt ? null : false)}
            className="btn-secondary text-sm py-2 px-4"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmBtnRef}
            type="button"
            onClick={() => closeWith(isPrompt ? value : true)}
            className={`text-sm py-2 px-4 rounded-xl font-medium transition-colors ${
              danger
                ? 'bg-red-500 hover:bg-red-400 text-white'
                : 'btn-primary'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
