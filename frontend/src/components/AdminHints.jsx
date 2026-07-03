import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { ArrowUp, ArrowDown, Trash2, Plus, Save, X, Lightbulb } from 'lucide-react';
import { listHints, createHint, updateHint, deleteHint } from '../api';
import { useConfirm } from './Confirm';
import { extractErrorMessage } from '../utils/apiError';

export default function AdminHints({ contestId }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [hints, setHints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // id of row being edited, or 'new'
  const [draft, setDraft] = useState({ label: '', body: '', cost_fraction: 0.1, order_idx: 0 });

  const refresh = () => {
    setLoading(true);
    listHints(contestId)
      .then((r) => setHints(r.data || []))
      .catch(() => toast.error(t('admin.users.toastFailed')))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  const startCreate = () => {
    setDraft({ label: '', body: '', cost_fraction: 0.1, order_idx: hints.length });
    setEditing('new');
  };

  const startEdit = (h) => {
    setDraft({ label: h.label, body: h.body, cost_fraction: h.cost_fraction, order_idx: h.order_idx });
    setEditing(h.id);
  };

  const save = async () => {
    try {
      const payload = {
        label: draft.label,
        body: draft.body,
        cost_fraction: Math.max(0, Math.min(1, parseFloat(draft.cost_fraction) || 0)),
        order_idx: parseInt(draft.order_idx, 10) || 0,
      };
      if (editing === 'new') await createHint(contestId, payload);
      else await updateHint(editing, payload);
      setEditing(null);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const remove = async (h) => {
    const ok = await confirm({
      message: t('adminHints.confirmDelete', { label: h.label || `#${h.id}` }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteHint(h.id);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  const reorder = async (h, dir) => {
    // Swap order_idx with the adjacent hint.
    const sorted = [...hints].sort((a, b) => a.order_idx - b.order_idx || a.id - b.id);
    const idx = sorted.findIndex((x) => x.id === h.id);
    const swap = dir === 'up' ? sorted[idx - 1] : sorted[idx + 1];
    if (!swap) return;
    try {
      await Promise.all([
        updateHint(h.id, { label: h.label, body: h.body, cost_fraction: h.cost_fraction, order_idx: swap.order_idx }),
        updateHint(swap.id, { label: swap.label, body: swap.body, cost_fraction: swap.cost_fraction, order_idx: h.order_idx }),
      ]);
      refresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 dark:bg-slate-800/30 dark:border-slate-700/40">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2 dark:text-gray-300">
          <Lightbulb className="w-4 h-4 text-amber-500 dark:text-amber-400" />
          {t('adminHints.heading')}
          <span className="text-xs font-normal text-slate-400 dark:text-gray-500">({hints.length})</span>
        </h4>
        {editing === null && (
          <button type="button" onClick={startCreate} className="btn-secondary text-xs py-1 px-2">
            <Plus className="w-3.5 h-3.5 mr-1 inline" />
            {t('adminHints.add')}
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-slate-400 italic dark:text-gray-600">{t('common.loading')}</p>
      ) : hints.length === 0 && editing !== 'new' ? (
        <p className="text-xs text-slate-400 italic dark:text-gray-600">{t('adminHints.empty')}</p>
      ) : (
        <ul className="space-y-2">
          {[...hints]
            .sort((a, b) => a.order_idx - b.order_idx || a.id - b.id)
            .map((h, i, arr) => (
              <li key={h.id} className="rounded-lg bg-white border border-gray-200 p-2 dark:bg-slate-900/40 dark:border-slate-700/40">
                {editing === h.id ? (
                  <HintForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => setEditing(null)} t={t} />
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="flex flex-col">
                      <button
                        type="button"
                        disabled={i === 0}
                        onClick={() => reorder(h, 'up')}
                        className="p-0.5 text-slate-400 hover:text-violet-500 disabled:opacity-30 disabled:cursor-not-allowed dark:text-gray-500 dark:hover:text-violet-400"
                        aria-label={t('adminHints.moveUp')}
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        disabled={i === arr.length - 1}
                        onClick={() => reorder(h, 'down')}
                        className="p-0.5 text-slate-400 hover:text-violet-500 disabled:opacity-30 disabled:cursor-not-allowed dark:text-gray-500 dark:hover:text-violet-400"
                        aria-label={t('adminHints.moveDown')}
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900 dark:text-white">
                          {h.label || `#${h.id}`}
                        </span>
                        <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-400">
                          -{Math.round((h.cost_fraction || 0) * 100)}%
                        </span>
                      </div>
                      {h.body && (
                        <p className="text-xs text-slate-500 mt-1 whitespace-pre-wrap dark:text-gray-400">{h.body}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => startEdit(h)}
                        className="p-1 rounded hover:bg-gray-100 text-slate-400 hover:text-violet-500 dark:hover:bg-slate-700/50"
                        aria-label={t('admin.contests.edit')}
                      >
                        <Save className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(h)}
                        className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500"
                        aria-label={t('admin.contests.delete')}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          {editing === 'new' && (
            <li className="rounded-lg bg-white border border-violet-300 p-2 dark:bg-slate-900/40 dark:border-violet-500/40">
              <HintForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => setEditing(null)} t={t} />
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function HintForm({ draft, setDraft, onSave, onCancel, t }) {
  return (
    <div className="space-y-2">
      <input
        type="text"
        className="input-field text-sm py-1.5"
        placeholder={t('adminHints.labelPlaceholder')}
        value={draft.label}
        onChange={(e) => setDraft({ ...draft, label: e.target.value })}
      />
      <textarea
        className="input-field text-sm py-1.5 min-h-[60px]"
        placeholder={t('adminHints.bodyPlaceholder')}
        value={draft.body}
        onChange={(e) => setDraft({ ...draft, body: e.target.value })}
      />
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500 dark:text-gray-400">
          {t('adminHints.costFraction')}
        </label>
        <input
          type="number"
          step={0.05}
          min={0}
          max={1}
          className="input-field text-sm py-1 w-20"
          value={draft.cost_fraction}
          onChange={(e) => setDraft({ ...draft, cost_fraction: e.target.value })}
        />
        <span className="text-xs text-slate-500 dark:text-gray-400">
          = {Math.round((parseFloat(draft.cost_fraction) || 0) * 100)}%
        </span>
        <div className="ml-auto flex gap-1">
          <button type="button" onClick={onSave} className="btn-primary text-xs py-1 px-2">
            <Save className="w-3.5 h-3.5 mr-1 inline" />
            {t('common.save')}
          </button>
          <button type="button" onClick={onCancel} className="btn-secondary text-xs py-1 px-2">
            <X className="w-3.5 h-3.5 mr-1 inline" />
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
