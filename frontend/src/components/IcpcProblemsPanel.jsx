import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import {
  Code, Trash2, RefreshCw, Clock, Cpu, Edit, Save, X, Plus, ChevronDown, ChevronUp,
  MessageCircle, FileDown, FileText, Upload, FileX,
} from 'lucide-react';
import {
  listIcpcProblems, deleteIcpcProblem, updateIcpcProblem, createIcpcProblem,
  listIcpcTestcases, addIcpcTestcase, updateIcpcTestcase, deleteIcpcTestcase,
  exportIcpcProblem,
  uploadIcpcProblemStatement, deleteIcpcProblemStatement,
  openStatementPdf,
} from '../api';
import { textOn } from '../utils/contrast';
import { useConfirm } from './Confirm';

const CHECKER_KINDS = [
  { value: 'tokens', labelKey: 'icpcProblems.checkerTokens' },
  { value: 'diff', labelKey: 'icpcProblems.checkerDiff' },
  { value: 'float', labelKey: 'icpcProblems.checkerFloat' },
  { value: 'interactive', labelKey: 'icpcProblems.checkerInteractive' },
];

const BLANK_DRAFT = {
  external_id: '',
  label: '',
  name: '',
  color: '#94a3b8',
  time_limit_ms: 1000,
  memory_limit_mb: 256,
  checker_kind: 'tokens',
  checker_epsilon: '',
  num_passes: 1,
  interactor_script: '',
  interactor_language: 'py3',
  scoring_mode: 'icpc',
  order_idx: 0,
};

const INTERACTOR_LANGUAGES = [
  { value: 'py3', labelKey: 'icpcProblems.interactorLangPy3' },
  { value: 'cpp', labelKey: 'icpcProblems.interactorLangCpp' },
  { value: 'c', labelKey: 'icpcProblems.interactorLangC' },
  { value: 'java', labelKey: 'icpcProblems.interactorLangJava' },
];

export default function IcpcProblemsPanel({ contestId }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null); // problem id or 'new'
  const [draft, setDraft] = useState(null);
  const [tcExpanded, setTcExpanded] = useState(null); // problem id whose testcases are shown

  const refresh = () => {
    setLoading(true);
    listIcpcProblems(contestId)
      .then((r) => setProblems(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // Reset state synchronously when the contest changes so we don't
    // briefly render the previous contest's problems under the new id.
    // Without this, closing + reopening the edit panel against a
    // different contest shows the stale list until the fetch resolves.
    setProblems([]);
    setEditingId(null);
    setDraft(null);
    setTcExpanded(null);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contestId]);

  const startEdit = (p) => {
    setDraft({
      external_id: p.external_id,
      label: p.label,
      name: p.name,
      color: p.color || '#94a3b8',
      time_limit_ms: p.time_limit_ms,
      memory_limit_mb: p.memory_limit_mb,
      checker_kind: p.checker_kind || 'tokens',
      checker_epsilon: '',
      num_passes: p.num_passes || 1,
      // The list endpoint doesn't return the script body (it's long + admin-
      // only). Leave blank; writing anything else replaces the current one,
      // leaving empty keeps whatever is stored. Admin can re-fetch via a
      // dedicated endpoint in v2 if they need to edit an existing script.
      interactor_script: '',
      interactor_language: p.interactor_language || 'py3',
      scoring_mode: p.scoring_mode || 'icpc',
      order_idx: p.order_idx,
    });
    setEditingId(p.id);
  };

  const startCreate = () => {
    setDraft({
      ...BLANK_DRAFT,
      label: String.fromCharCode(65 + problems.length),  // next free letter
      order_idx: problems.length,
    });
    setEditingId('new');
  };

  const save = async () => {
    try {
      const payload = {
        external_id: draft.external_id.trim(),
        label: draft.label.trim(),
        name: draft.name.trim(),
        color: draft.color || '',
        time_limit_ms: parseInt(draft.time_limit_ms, 10) || 1000,
        memory_limit_mb: parseInt(draft.memory_limit_mb, 10) || 256,
        checker_kind: draft.checker_kind,
        checker_epsilon: draft.checker_kind === 'float'
          ? (parseFloat(draft.checker_epsilon) || 1e-6)
          : null,
        num_passes: Math.max(1, parseInt(draft.num_passes, 10) || 1),
        interactor_script: draft.checker_kind === 'interactive'
          ? (draft.interactor_script || '').trim() || null
          : null,
        interactor_language: draft.checker_kind === 'interactive'
          ? (draft.interactor_language || 'py3')
          : 'py3',
        scoring_mode: draft.scoring_mode === 'subtasks' ? 'subtasks' : 'icpc',
        order_idx: parseInt(draft.order_idx, 10) || 0,
      };
      if (!payload.external_id || !payload.label || !payload.name) {
        toast.error(t('icpcProblems.toastMissingFields'));
        return;
      }
      if (editingId === 'new') {
        await createIcpcProblem(contestId, payload);
        toast.success(t('icpcProblems.toastCreated'));
      } else {
        await updateIcpcProblem(editingId, payload);
        toast.success(t('icpcProblems.toastSaved'));
      }
      setEditingId(null);
      setDraft(null);
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const remove = async (p) => {
    const ok = await confirm({
      message: t('icpcProblems.confirmDelete', { label: p.label, name: p.name }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteIcpcProblem(p.id);
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 dark:bg-slate-800/30 dark:border-slate-700/40">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2 dark:text-gray-300">
          <Code className="w-4 h-4 text-violet-500 dark:text-violet-400" />
          {t('icpcProblems.heading')}
          <span className="text-xs font-normal text-slate-400 dark:text-gray-500">({problems.length})</span>
        </h4>
        <div className="flex items-center gap-2">
          {editingId === null && (
            <button type="button" onClick={startCreate} className="btn-secondary text-xs py-1 px-2">
              <Plus className="w-3.5 h-3.5 mr-1 inline" />
              {t('icpcProblems.add')}
            </button>
          )}
          <button type="button" onClick={refresh} className="btn-secondary text-xs py-1 px-2" title={t('common.refresh')}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {editingId === 'new' && draft && (
        <div className="rounded-lg bg-white border-2 border-violet-300 p-3 dark:bg-slate-900/40 dark:border-violet-500/40">
          <EditForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => { setEditingId(null); setDraft(null); }} t={t} isNew />
        </div>
      )}

      {loading ? (
        <p className="text-xs text-slate-400 italic dark:text-gray-600">{t('common.loading')}</p>
      ) : problems.length === 0 && editingId !== 'new' ? (
        <p className="text-xs text-slate-400 italic dark:text-gray-600">{t('icpcProblems.empty')}</p>
      ) : (
        <ul className="space-y-2">
          {problems.map((p) => (
            <li key={p.id} className="rounded-lg bg-white border border-gray-200 p-3 dark:bg-slate-900/40 dark:border-slate-700/40">
              {editingId === p.id ? (
                <EditForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => { setEditingId(null); setDraft(null); }} t={t} />
              ) : (
                <>
                  <div className="flex items-center gap-3">
                    <span
                      className="w-8 h-8 rounded text-sm font-bold flex items-center justify-center flex-shrink-0"
                      style={{
                        background: p.color || '#94a3b8',
                        color: textOn(p.color || '#94a3b8'),
                      }}
                    >
                      {p.label}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900 truncate dark:text-white">{p.name}</p>
                      <p className="text-[11px] text-slate-500 dark:text-gray-500 flex items-center gap-3 flex-wrap">
                        <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" />{(p.time_limit_ms / 1000).toFixed(1)} s</span>
                        <span className="inline-flex items-center gap-1"><Cpu className="w-3 h-3" />{p.memory_limit_mb} MiB</span>
                        <span className="font-mono">{p.external_id}</span>
                        <span className="uppercase tracking-wide font-semibold text-slate-400 dark:text-gray-600">{p.checker_kind}</span>
                        {p.num_passes > 1 && <span className="text-violet-600 dark:text-violet-400">×{p.num_passes}</span>}
                        {p.has_interactor && (
                          <span className="text-sky-600 inline-flex items-center gap-1 dark:text-sky-400">
                            <MessageCircle className="w-3 h-3" />
                            {t('icpcProblems.interactive')}
                          </span>
                        )}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setTcExpanded(tcExpanded === p.id ? null : p.id)}
                      className="p-1.5 rounded hover:bg-gray-100 text-slate-400 hover:text-slate-600 flex-shrink-0 dark:hover:bg-slate-700/50"
                      title={t('icpcProblems.toggleTestcases')}
                    >
                      {tcExpanded === p.id ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => startEdit(p)}
                      className="p-1.5 rounded hover:bg-gray-100 text-slate-400 hover:text-violet-500 dark:hover:bg-slate-700/50 dark:hover:text-violet-400 flex-shrink-0"
                      title={t('icpcProblems.edit')}
                      aria-label={t('icpcProblems.edit')}
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </button>
                    <StatementPdfControls
                      problem={p}
                      contestId={contestId}
                      onChanged={refresh}
                      t={t}
                      confirm={confirm}
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const r = await exportIcpcProblem(p.id);
                          const url = URL.createObjectURL(r.data);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${p.external_id || 'problem'}.zip`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                        } catch (err) {
                          toast.error(err.response?.data?.detail || t('icpcProblems.exportFailed'));
                        }
                      }}
                      className="p-1.5 rounded hover:bg-gray-100 text-slate-400 hover:text-sky-500 dark:hover:bg-slate-700/50 dark:hover:text-sky-400 flex-shrink-0"
                      title={t('icpcProblems.exportZip')}
                      aria-label={t('icpcProblems.exportZip')}
                    >
                      <FileDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(p)}
                      className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 flex-shrink-0 dark:text-gray-500 dark:hover:text-red-400"
                      title={t('admin.contests.delete')}
                      aria-label={t('admin.contests.delete')}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {tcExpanded === p.id && <TestcaseEditor problemId={p.id} t={t} />}
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


function EditForm({ draft, setDraft, onSave, onCancel, t, isNew }) {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[60px_1fr_80px] gap-2">
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.labelField')}</label>
          <input type="text" className="input-field text-sm py-1 px-2" maxLength={8}
            value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.nameField')}</label>
          <input type="text" className="input-field text-sm py-1 px-2"
            value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.colorField')}</label>
          <input type="color" className="input-field h-[32px] p-0.5"
            value={draft.color || '#94a3b8'} onChange={(e) => setDraft({ ...draft, color: e.target.value })} />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.timeField')}</label>
          <input type="number" min={100} className="input-field text-sm py-1 px-2"
            value={draft.time_limit_ms} onChange={(e) => setDraft({ ...draft, time_limit_ms: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.memoryField')}</label>
          <input type="number" min={32} className="input-field text-sm py-1 px-2"
            value={draft.memory_limit_mb} onChange={(e) => setDraft({ ...draft, memory_limit_mb: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.extField')}</label>
          <input type="text" className="input-field text-sm py-1 px-2 font-mono" maxLength={64}
            value={draft.external_id} onChange={(e) => setDraft({ ...draft, external_id: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.passesField')}</label>
          <input type="number" min={1} max={20} className="input-field text-sm py-1 px-2"
            value={draft.num_passes} onChange={(e) => setDraft({ ...draft, num_passes: e.target.value })} />
        </div>
      </div>
      <div className="grid grid-cols-[1fr_120px] gap-2">
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.checkerField')}</label>
          <select className="input-field text-sm py-1 px-2"
            value={draft.checker_kind} onChange={(e) => setDraft({ ...draft, checker_kind: e.target.value })}>
            {CHECKER_KINDS.map((c) => (
              <option key={c.value} value={c.value}>{t(c.labelKey)}</option>
            ))}
          </select>
        </div>
        {draft.checker_kind === 'float' && (
          <div>
            <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.epsilonField')}</label>
            <input type="text" placeholder="1e-6" className="input-field text-sm py-1 px-2 font-mono"
              value={draft.checker_epsilon} onChange={(e) => setDraft({ ...draft, checker_epsilon: e.target.value })} />
          </div>
        )}
      </div>
      <div>
        <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">
          {t('icpcProblems.scoringModeField')}
        </label>
        <select
          className="input-field text-sm py-1 px-2"
          value={draft.scoring_mode}
          onChange={(e) => setDraft({ ...draft, scoring_mode: e.target.value })}
        >
          <option value="icpc">{t('icpcProblems.scoringModeIcpc')}</option>
          <option value="subtasks">{t('icpcProblems.scoringModeSubtasks')}</option>
        </select>
        <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
          {draft.scoring_mode === 'subtasks'
            ? t('icpcProblems.scoringModeSubtasksHint')
            : t('icpcProblems.scoringModeIcpcHint')}
        </p>
      </div>
      {draft.checker_kind === 'interactive' && (
        <div className="space-y-2">
          <div>
            <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.interactorLanguageField')}</label>
            <select
              className="input-field text-sm py-1 px-2"
              value={draft.interactor_language}
              onChange={(e) => setDraft({ ...draft, interactor_language: e.target.value })}
            >
              {INTERACTOR_LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{t(l.labelKey)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.interactorField')}</label>
            <textarea
              className="input-field text-xs font-mono min-h-[140px]"
              placeholder={t('icpcProblems.interactorPlaceholder')}
              value={draft.interactor_script}
              onChange={(e) => setDraft({ ...draft, interactor_script: e.target.value })}
            />
            <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
              {draft.interactor_language === 'py3'
                ? t('icpcProblems.interactorHint')
                : t('icpcProblems.interactorHintCompiled')}
            </p>
          </div>
        </div>
      )}
      <p className="text-[11px] text-slate-400 dark:text-gray-500">
        {draft.checker_kind === 'float' ? t('icpcProblems.floatHint')
          : draft.checker_kind === 'diff' ? t('icpcProblems.diffHint')
          : draft.checker_kind === 'interactive' ? t('icpcProblems.interactiveHint')
          : t('icpcProblems.tokensHint')}
      </p>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onSave} className="btn-primary text-xs py-1 px-3">
          <Save className="w-3.5 h-3.5 mr-1 inline" />
          {isNew ? t('common.create') : t('common.save')}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary text-xs py-1 px-3">
          <X className="w-3.5 h-3.5 mr-1 inline" />
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}


function TestcaseEditor({ problemId, t }) {
  const confirm = useConfirm();
  const [testcases, setTestcases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState(null);

  const refresh = () => {
    setLoading(true);
    listIcpcTestcases(problemId)
      .then((r) => setTestcases(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [problemId]);

  const startCreate = () => {
    setDraft({ rank: testcases.length, is_sample: false, input_data: '', expected_output: '', points: 1, group_name: '' });
    setEditingId('new');
  };
  const startEdit = (tc) => {
    setDraft({ rank: tc.rank, is_sample: tc.is_sample, input_data: tc.input_data, expected_output: tc.expected_output, points: tc.points, group_name: tc.group_name || '' });
    setEditingId(tc.id);
  };
  const save = async () => {
    try {
      const payload = {
        rank: parseInt(draft.rank, 10) || 0,
        is_sample: !!draft.is_sample,
        input_data: draft.input_data || '',
        expected_output: draft.expected_output || '',
        points: parseInt(draft.points, 10) || 1,
        group_name: (draft.group_name || '').trim() || null,
      };
      if (editingId === 'new') await addIcpcTestcase(problemId, payload);
      else await updateIcpcTestcase(editingId, payload);
      setEditingId(null); setDraft(null);
      refresh();
      toast.success(t('icpcProblems.toastTcSaved'));
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };
  const remove = async (tc) => {
    const ok = await confirm({
      message: t('icpcProblems.tcConfirmDelete', { rank: tc.rank }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteIcpcTestcase(tc.id);
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  return (
    <div className="mt-3 border-t border-gray-200 dark:border-slate-700/40 pt-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-600 dark:text-gray-400">
          {t('icpcProblems.tcHeading', { n: testcases.length })}
        </p>
        {editingId === null && (
          <button type="button" onClick={startCreate} className="btn-secondary text-xs py-0.5 px-2">
            <Plus className="w-3 h-3 mr-1 inline" />{t('icpcProblems.tcAdd')}
          </button>
        )}
      </div>
      {loading ? (
        <p className="text-[11px] text-slate-400 italic">{t('common.loading')}</p>
      ) : (
        <ul className="space-y-1.5">
          {editingId === 'new' && (
            <li className="rounded bg-violet-500/5 border border-violet-300 p-2 dark:border-violet-500/40">
              <TestcaseForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => { setEditingId(null); setDraft(null); }} t={t} />
            </li>
          )}
          {testcases.map((tc) => (
            <li key={tc.id} className="rounded border border-gray-200 p-2 dark:border-slate-700/40">
              {editingId === tc.id ? (
                <TestcaseForm draft={draft} setDraft={setDraft} onSave={save} onCancel={() => { setEditingId(null); setDraft(null); }} t={t} />
              ) : (
                <div className="flex items-center gap-2 text-xs">
                  <span className={`px-1.5 py-0.5 rounded font-medium ${
                    tc.is_sample ? 'bg-sky-500/15 text-sky-700 dark:text-sky-300' : 'bg-slate-500/15 text-slate-600 dark:text-gray-400'
                  }`}>
                    #{tc.rank} {tc.is_sample ? t('icpcProblems.tcSample') : t('icpcProblems.tcSecret')}
                  </span>
                  <span className="text-slate-500 dark:text-gray-500 flex-1 truncate font-mono">
                    in: {(tc.input_data || '').slice(0, 40)}
                  </span>
                  <button type="button" onClick={() => startEdit(tc)} className="p-1 rounded hover:bg-gray-100 text-slate-400 hover:text-violet-500 dark:hover:bg-slate-700/50">
                    <Edit className="w-3 h-3" />
                  </button>
                  <button type="button" onClick={() => remove(tc)} className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


function TestcaseForm({ draft, setDraft, onSave, onCancel, t }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className="text-[10px] text-slate-500 dark:text-gray-400 inline-flex items-center gap-1">
          <span>{t('icpcProblems.tcRankField')}</span>
          <input type="number" className="input-field text-xs py-0.5 px-1 w-14" min={0}
            value={draft.rank} onChange={(e) => setDraft({ ...draft, rank: e.target.value })} />
        </label>
        <label className="text-[10px] text-slate-500 dark:text-gray-400 inline-flex items-center gap-1">
          <input type="checkbox" checked={!!draft.is_sample}
            onChange={(e) => setDraft({ ...draft, is_sample: e.target.checked })} />
          <span>{t('icpcProblems.tcIsSample')}</span>
        </label>
        <label className="text-[10px] text-slate-500 dark:text-gray-400 inline-flex items-center gap-1">
          <span>{t('icpcProblems.tcPointsField')}</span>
          <input type="number" min={1} className="input-field text-xs py-0.5 px-1 w-14"
            value={draft.points} onChange={(e) => setDraft({ ...draft, points: e.target.value })} />
        </label>
        <label className="text-[10px] text-slate-500 dark:text-gray-400 inline-flex items-center gap-1">
          <span>{t('icpcProblems.tcGroupField')}</span>
          <input type="text" className="input-field text-xs py-0.5 px-1 w-24" maxLength={64}
            placeholder="easy"
            value={draft.group_name || ''}
            onChange={(e) => setDraft({ ...draft, group_name: e.target.value })} />
        </label>
      </div>
      <div className="grid sm:grid-cols-2 gap-2">
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.tcInputField')}</label>
          <textarea className="input-field text-xs font-mono min-h-[80px]"
            value={draft.input_data}
            onChange={(e) => setDraft({ ...draft, input_data: e.target.value })} />
        </div>
        <div>
          <label className="block text-[10px] uppercase text-slate-400 dark:text-gray-500">{t('icpcProblems.tcExpectedField')}</label>
          <textarea className="input-field text-xs font-mono min-h-[80px]"
            value={draft.expected_output}
            onChange={(e) => setDraft({ ...draft, expected_output: e.target.value })} />
        </div>
      </div>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onSave} className="btn-primary text-xs py-0.5 px-2">
          <Save className="w-3 h-3 mr-1 inline" />{t('common.save')}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary text-xs py-0.5 px-2">
          <X className="w-3 h-3 mr-1 inline" />{t('common.cancel')}
        </button>
      </div>
    </div>
  );
}


function StatementPdfControls({ problem, contestId, onChanged, t, confirm }) {
  const fileInputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const openPreview = () => {
    // Open via a short-lived stream ticket + blob fetch so the durable
    // session token never lands in a URL. ``v`` (the file mtime) still
    // busts any stale browser cache after an admin replaces the PDF.
    openStatementPdf(contestId, problem.id, problem.statement_pdf_version || 0)
      .catch(() => toast.error(t('icpcProblems.pdfOpenFailed')));
  };

  const onPick = () => fileInputRef.current?.click();

  const onFileChosen = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (file.type && file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      toast.error(t('icpcProblems.pdfNotPdf'));
      return;
    }
    setBusy(true);
    try {
      await uploadIcpcProblemStatement(problem.id, file);
      toast.success(t('icpcProblems.pdfUploaded'));
      onChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('icpcProblems.pdfUploadFailed'));
    } finally {
      setBusy(false);
    }
  };

  const onRemove = async () => {
    const ok = await confirm({
      message: t('icpcProblems.pdfConfirmDelete', { label: problem.label, name: problem.name }),
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await deleteIcpcProblemStatement(problem.id);
      toast.success(t('icpcProblems.pdfDeleted'));
      onChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={onFileChosen}
      />
      {problem.has_statement_pdf && (
        <button
          type="button"
          onClick={openPreview}
          disabled={busy}
          className="p-1.5 rounded hover:bg-gray-100 text-slate-400 hover:text-emerald-500 dark:hover:bg-slate-700/50 dark:hover:text-emerald-400 flex-shrink-0 disabled:opacity-50"
          title={t('icpcProblems.pdfView')}
          aria-label={t('icpcProblems.pdfView')}
        >
          <FileText className="w-3.5 h-3.5" />
        </button>
      )}
      <button
        type="button"
        onClick={onPick}
        disabled={busy}
        className="p-1.5 rounded hover:bg-gray-100 text-slate-400 hover:text-violet-500 dark:hover:bg-slate-700/50 dark:hover:text-violet-400 flex-shrink-0 disabled:opacity-50"
        title={problem.has_statement_pdf ? t('icpcProblems.pdfReplace') : t('icpcProblems.pdfUpload')}
        aria-label={problem.has_statement_pdf ? t('icpcProblems.pdfReplace') : t('icpcProblems.pdfUpload')}
      >
        <Upload className="w-3.5 h-3.5" />
      </button>
      {problem.has_statement_pdf && (
        <button
          type="button"
          onClick={onRemove}
          disabled={busy}
          className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 flex-shrink-0 dark:text-gray-500 dark:hover:text-red-400 disabled:opacity-50"
          title={t('icpcProblems.pdfRemove')}
          aria-label={t('icpcProblems.pdfRemove')}
        >
          <FileX className="w-3.5 h-3.5" />
        </button>
      )}
    </>
  );
}
