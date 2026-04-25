import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { Navigate, Link } from 'react-router-dom';
import {
  getUsers,
  getContests, getContest, createContest, updateContest, deleteContest,
  createInstance, deleteInstance,
  uploadProblemStatement, deleteProblemStatement,
  testScoring, rescoreContest,
  listContestParticipants, addContestParticipantUser, addContestParticipantTeam,
  removeContestParticipant, browseTeams,
  duplicateContest, importDomjudgePackage,
} from '../api';
import {
  Users, Trophy, Plus, Trash2, Shield, Edit,
  Save, X, Upload, FileText, FileDown, Code, Target, Eye, Package, FileType,
  FlaskConical, RefreshCw, ScrollText, UserPlus, UserMinus, Lock, Globe,
  Inbox, Cpu, Copy, Building2, Pause, Play,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import PackagesPanel from '../components/PackagesPanel';
import ScoringPanel from '../components/ScoringPanel';
import AdminHints from '../components/AdminHints';
import IcpcProblemsPanel from '../components/IcpcProblemsPanel';
import IcpcStatsPanel from '../components/IcpcStatsPanel';
import AffiliationsPanel from '../components/AffiliationsPanel';
import WorkersPanel from '../components/WorkersPanel';
import UsersTab from '../components/admin/UsersTab';
import AuditLogTab from '../components/admin/AuditLogTab';
import SubmissionsTab from '../components/admin/SubmissionsTab';
import EditInstanceModal from '../components/admin/EditInstanceModal';
import { useConfirm } from '../components/Confirm';
import { toUtcIso, toLocalInputValue, formatDateTime } from '../utils/datetime';

const DEFAULT_SCRIPT = '# Variables disponibles : instance_data, submission_data\n# Définissez la variable score\n\nlines = submission_data.strip().split("\\n")\nscore = len(lines)\n';

export default function Admin() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [tab, setTab] = useState('contests');
  const [users, setUsers] = useState([]);
  const [contests, setContests] = useState([]);
  // ICPC-only: DOMjudge package file to import right after the contest
  // is created (so the admin doesn't need a second edit-save round trip).
  const [createIcpcPackage, setCreateIcpcPackage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editContest, setEditContest] = useState(null);
  const [showForm, setShowForm] = useState(false);
  // Step 1 of contest creation — admin picks "output scoring" vs "ICPC"
  // before any form shows up. Cleaner than hiding a dropdown in the middle
  // of the long form.
  const [showKindPicker, setShowKindPicker] = useState(false);
  const [instanceFile, setInstanceFile] = useState(null);
  const [instanceForm, setInstanceForm] = useState({
    name: '',
    unlock_delay_minutes: 0,
    unlock_at_absolute: '',
    unlock_mode: 'relative', // 'relative' | 'absolute'
  });
  // Instance currently being edited (full row) — opens the edit modal.
  const [editingInstance, setEditingInstance] = useState(null);
  // A PDF selected at creation time. Uploaded as a follow-up call after the
  // contest has an ID. Cleared once the form is submitted.
  const [createPdfFile, setCreatePdfFile] = useState(null);
  const [rescoring, setRescoring] = useState(false);
  const [testScoringOpen, setTestScoringOpen] = useState(false);
  const [testScoringState, setTestScoringState] = useState({
    instance_id: '',
    submission_data: '',
    useOverride: false,
    result: null,
    running: false,
  });
  const [contestForm, setContestForm] = useState({
    title: '', description: '', problem_statement: '',
    visible_at: '', start_time: '', end_time: '', hidden_at: '', freeze_scoreboard_at: '',
    participation_mode: 'team',
    is_public: true,
    practice_mode: false,
    kind: 'output',
    dedup_block: false,
    min_seconds_between_submits: 0,
    max_submissions_per_instance: '',
    output_validator_script: '',
    scoring_script: DEFAULT_SCRIPT,
  });
  const [participants, setParticipants] = useState([]);
  const [participantUserId, setParticipantUserId] = useState('');
  const [participantTeamId, setParticipantTeamId] = useState('');
  const [allTeams, setAllTeams] = useState([]);

  const isAdmin = user?.is_admin;

  const refresh = async () => {
    if (!isAdmin) return;
    try {
      const [u, c] = await Promise.all([getUsers(), getContests()]);
      setUsers(u.data);
      const fullContests = await Promise.all(
        c.data.map((ct) => getContest(ct.id).then((r) => r.data))
      );
      setContests(fullContests);
    } catch {
      toast.error(t('admin.contests.toastLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [isAdmin]);

  if (!isAdmin) return <Navigate to="/dashboard" replace />;

  const handleContestSubmit = async (e) => {
    e.preventDefault();
    const isIcpc = contestForm.kind === 'icpc';
    try {
      // Strip Hashcode-only fields when saving an ICPC contest so the
      // backend doesn't store stale data that would confuse the judging
      // pipeline if someone flips the kind later.
      const commonPayload = {
        title: contestForm.title,
        description: contestForm.description,
        visible_at: toUtcIso(contestForm.visible_at),
        start_time: toUtcIso(contestForm.start_time),
        end_time: toUtcIso(contestForm.end_time),
        hidden_at: toUtcIso(contestForm.hidden_at),
        freeze_scoreboard_at: toUtcIso(contestForm.freeze_scoreboard_at),
        participation_mode: contestForm.participation_mode,
        is_public: contestForm.is_public,
        kind: contestForm.kind,
        practice_mode: contestForm.practice_mode,
        dedup_block: contestForm.dedup_block,
        min_seconds_between_submits: parseInt(contestForm.min_seconds_between_submits || 0, 10) || 0,
      };
      const payload = isIcpc
        ? commonPayload
        : {
            ...commonPayload,
            problem_statement: contestForm.problem_statement,
            scoring_script: contestForm.scoring_script,
            output_validator_script: (contestForm.output_validator_script || '').trim() || null,
            max_submissions_per_instance:
              contestForm.max_submissions_per_instance === '' || contestForm.max_submissions_per_instance == null
                ? null
                : parseInt(contestForm.max_submissions_per_instance, 10),
          };

      if (editContest) {
        await updateContest(editContest.id, payload);
        toast.success(t('admin.contests.toastUpdated'));
      } else {
        const { data: created } = await createContest(payload);
        // Output contest: optional per-contest PDF.
        if (!isIcpc && createPdfFile) {
          const MAX_BYTES = 10 * 1024 * 1024;
          if (createPdfFile.size > MAX_BYTES) {
            toast.error(t('admin.form.toastPdfTooLarge'));
          } else {
            try {
              await uploadProblemStatement(created.id, createPdfFile);
            } catch (err) {
              toast.error(err.response?.data?.detail || t('admin.form.toastPdfUploadFailed'));
            }
          }
        }
        // ICPC contest: if the admin attached a DOMjudge package, import it
        // now so the contest ships with problems + testcases on first save.
        if (isIcpc && createIcpcPackage) {
          try {
            const { data } = await importDomjudgePackage(created.id, createIcpcPackage);
            toast.success(t('admin.form.toastImportOk', {
              problems: data.problems_imported,
              testcases: data.testcases_imported,
            }));
          } catch (err) {
            toast.error(err.response?.data?.detail || t('admin.form.toastImportFailed'));
          }
        }
        toast.success(t('admin.contests.toastCreated'));
      }
      setShowForm(false);
      setEditContest(null);
      setCreatePdfFile(null);
      setCreateIcpcPackage(null);
      resetContestForm();
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.contests.toastFailed'));
    }
  };

  const resetContestForm = () => {
    setContestForm({
      title: '', description: '', problem_statement: '',
      visible_at: '', start_time: '', end_time: '', hidden_at: '', freeze_scoreboard_at: '',
      participation_mode: 'team',
      is_public: true,
      practice_mode: false,
      dedup_block: false,
      min_seconds_between_submits: 0,
      max_submissions_per_instance: '',
      output_validator_script: '',
      scoring_script: DEFAULT_SCRIPT,
    });
    setParticipants([]);
    setParticipantUserId('');
  };

  const refreshParticipants = async (contestId) => {
    try {
      const [pRes, tRes] = await Promise.all([
        listContestParticipants(contestId),
        browseTeams(),
      ]);
      setParticipants(pRes.data);
      setAllTeams(tRes.data || []);
    } catch {
      setParticipants([]);
    }
  };

  const startEdit = async (contest) => {
    try {
      const { data: full } = await getContest(contest.id);
      setEditContest(full);
      setContestForm({
        title: full.title || '',
        description: full.description || '',
        problem_statement: full.problem_statement || '',
        visible_at: toLocalInputValue(full.visible_at),
        start_time: toLocalInputValue(full.start_time),
        end_time: toLocalInputValue(full.end_time),
        hidden_at: toLocalInputValue(full.hidden_at),
        freeze_scoreboard_at: toLocalInputValue(full.freeze_scoreboard_at),
        participation_mode: full.participation_mode || 'team',
        is_public: full.is_public !== false,
        practice_mode: !!full.practice_mode,
        kind: full.kind || 'output',
        dedup_block: !!full.dedup_block,
        min_seconds_between_submits: full.min_seconds_between_submits || 0,
        max_submissions_per_instance: full.max_submissions_per_instance ?? '',
        output_validator_script: full.output_validator_script || '',
        scoring_script: full.scoring_script || '',
      });
      setParticipantUserId('');
      refreshParticipants(full.id);
      setShowForm(true);
    } catch {
      toast.error(t('admin.contests.toastLoadDetailsFailed'));
    }
  };

  const handleAddParticipantUser = async () => {
    if (!editContest || !participantUserId) return;
    try {
      await addContestParticipantUser(editContest.id, parseInt(participantUserId, 10));
      toast.success(t('admin.form.toastParticipantAdded'));
      setParticipantUserId('');
      refreshParticipants(editContest.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastParticipantAddFailed'));
    }
  };

  const handleAddParticipantTeam = async () => {
    if (!editContest || !participantTeamId) return;
    try {
      await addContestParticipantTeam(editContest.id, parseInt(participantTeamId, 10));
      toast.success(t('admin.form.toastParticipantAdded'));
      setParticipantTeamId('');
      refreshParticipants(editContest.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastParticipantAddFailed'));
    }
  };

  const handleRemoveParticipant = async (entryId) => {
    if (!editContest) return;
    try {
      await removeContestParticipant(editContest.id, entryId);
      toast.success(t('admin.form.toastParticipantRemoved'));
      refreshParticipants(editContest.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastParticipantRemoveFailed'));
    }
  };

  const handleDeleteContest = async (id, title) => {
    const ok = await confirm({
      message: t('admin.contests.confirmDelete', { title }),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteContest(id);
      toast.success(t('admin.contests.toastDeleted'));
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.contests.toastFailed'));
    }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !editContest) return;
    const MAX_BYTES = 10 * 1024 * 1024;
    if (file.size > MAX_BYTES) {
      toast.error(t('admin.form.toastPdfTooLarge'));
      return;
    }
    const toastId = toast.loading(t('admin.form.toastPdfUploading'));
    try {
      const { data } = await uploadProblemStatement(editContest.id, file);
      setEditContest(data);
      toast.success(t('admin.form.toastPdfUploaded'), { id: toastId });
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastPdfUploadFailed'), { id: toastId });
    }
  };

  const handlePdfRemove = async () => {
    if (!editContest) return;
    const ok = await confirm({
      message: t('admin.form.confirmRemovePdf'),
      danger: true,
    });
    if (!ok) return;
    const toastId = toast.loading(t('admin.form.toastPdfRemoving'));
    try {
      const { data } = await deleteProblemStatement(editContest.id);
      setEditContest(data);
      toast.success(t('admin.form.toastPdfRemoved'), { id: toastId });
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastPdfRemoveFailed'), { id: toastId });
    }
  };

  // Shared uploader for scoring + validator scripts. ``field`` is the
  // key on contestForm to write the uploaded contents to.
  const uploadScriptInto = async (e, field) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const MAX_BYTES = 256 * 1024;
    if (file.size > MAX_BYTES) {
      toast.error(t('admin.form.toastScriptTooLarge'));
      return;
    }
    try {
      const text = await file.text();
      setContestForm((f) => ({ ...f, [field]: text }));
      toast.success(t('admin.form.toastLoaded', { name: file.name }));
    } catch {
      toast.error(t('admin.form.toastScriptReadFailed'));
    }
  };
  const handleScriptUpload = (e) => uploadScriptInto(e, 'scoring_script');
  const handleValidatorUpload = (e) => uploadScriptInto(e, 'output_validator_script');

  const openTestScoring = (mode = 'score') => {
    setTestScoringState({
      instance_id: editContest?.instances?.[0]?.id ? String(editContest.instances[0].id) : '',
      submission_data: '',
      useOverride: true,
      result: null,
      running: false,
      mode,  // "score" | "validate"
    });
    setTestScoringOpen(true);
  };

  const runTestScoring = async (e) => {
    e.preventDefault();
    if (!editContest || !testScoringState.instance_id) return;
    setTestScoringState((s) => ({ ...s, running: true, result: null }));
    try {
      const isValidate = testScoringState.mode === 'validate';
      const payload = {
        instance_id: parseInt(testScoringState.instance_id, 10),
        submission_data: testScoringState.submission_data,
        mode: isValidate ? 'validate' : 'score',
      };
      if (testScoringState.useOverride) {
        if (isValidate) {
          payload.validator_override = contestForm.output_validator_script || '';
        } else {
          payload.script_override = contestForm.scoring_script;
        }
      }
      const { data } = await testScoring(editContest.id, payload);
      setTestScoringState((s) => ({ ...s, running: false, result: data }));
    } catch (err) {
      setTestScoringState((s) => ({
        ...s,
        running: false,
        result: { ok: false, error: err.response?.data?.detail || 'Échec' },
      }));
    }
  };

  const downloadAsPy = (content, baseName) => {
    if (!content) return;
    const safe = (contestForm.title || baseName).replace(/[^a-zA-Z0-9._-]+/g, '_');
    const blob = new Blob([content], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safe}-${baseName}.py`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };
  const handleScriptDownload = () =>
    downloadAsPy(contestForm.scoring_script, 'scoring');
  const handleValidatorDownload = () =>
    downloadAsPy(contestForm.output_validator_script, 'validator');

  const handleAddInstance = async (contestId) => {
    if (!instanceFile || !instanceForm.name) {
      toast.error(t('admin.contests.toastNeedFields'));
      return;
    }
    try {
      const fd = new FormData();
      fd.append('name', instanceForm.name);
      if (instanceForm.unlock_mode === 'absolute' && instanceForm.unlock_at_absolute) {
        fd.append('unlock_delay_seconds', '0');
        fd.append('unlock_at_absolute', toUtcIso(instanceForm.unlock_at_absolute) || '');
      } else {
        const delay = Math.max(0, Math.floor(Number(instanceForm.unlock_delay_minutes) || 0) * 60);
        fd.append('unlock_delay_seconds', String(delay));
      }
      fd.append('file', instanceFile);
      await createInstance(contestId, fd);
      toast.success(t('admin.instance.toastAdded'));
      setInstanceFile(null);
      setInstanceForm({ name: '', unlock_delay_minutes: 0, unlock_at_absolute: '', unlock_mode: 'relative' });
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  const handleRescore = async () => {
    if (!editContest) return;
    const ok = await confirm({
      message: t('admin.form.confirmRescore', { title: editContest.title }),
    });
    if (!ok) return;
    setRescoring(true);
    try {
      const { data } = await rescoreContest(editContest.id);
      toast.success(t('admin.form.toastRescoreDone', {
        s: data.succeeded, u: data.unchanged, f: data.failed,
      }));
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.form.toastRescoreFailed'));
    } finally {
      setRescoring(false);
    }
  };

  const handleDeleteInstance = async (id) => {
    const ok = await confirm({
      message: t('admin.instance.confirmDelete'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteInstance(id);
      toast.success(t('admin.instance.toastDeleted'));
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3 dark:text-white">
          <Shield className="w-8 h-8 text-amber-500 dark:text-amber-400" />
          {t('admin.title')}
        </h1>
        <p className="text-slate-500 mt-1 dark:text-gray-400">{t('admin.subtitle')}</p>
      </div>

      <div className="flex gap-1 bg-white/50 p-1 rounded-xl w-fit border border-gray-200 dark:bg-slate-900/50 dark:border-slate-800/50">
        {[
          { key: 'contests', label: t('admin.tabContests'), icon: Trophy },
          { key: 'submissions', label: t('admin.tabSubmissions'), icon: Inbox },
          { key: 'users', label: t('admin.tabUsers'), icon: Users },
          { key: 'affiliations', label: t('admin.tabAffiliations'), icon: Building2 },
          { key: 'workers', label: t('admin.tabWorkers'), icon: Cpu },
          { key: 'packages', label: t('admin.tabPackages'), icon: Package },
          { key: 'scoring', label: t('admin.tabScoring'), icon: Cpu },
          { key: 'audit', label: t('admin.tabAudit'), icon: ScrollText },
        ].map((tb) => (
          <button
            key={tb.key}
            onClick={() => setTab(tb.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === tb.key
                ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20'
                : 'text-slate-500 hover:text-slate-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-slate-800/50'
            }`}
          >
            <tb.icon className="w-4 h-4" />
            {tb.label}
          </button>
        ))}
      </div>

      {tab === 'affiliations' && <AffiliationsPanel />}
      {tab === 'workers' && <WorkersPanel />}

      {tab === 'users' && (
        <UsersTab users={users} currentUser={user} onChange={refresh} />
      )}

      {tab === 'contests' && (
        <div className="space-y-6">
          <button
            onClick={() => {
              resetContestForm();
              setEditContest(null);
              setShowKindPicker(true);
            }}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2 inline" />
            {t('admin.contests.new')}
          </button>

          {showKindPicker && (
            <div
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
              onClick={() => setShowKindPicker(false)}
            >
              <div
                className="glass-card p-6 w-full max-w-2xl animate-slide-up"
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                    {t('admin.kindPicker.title')}
                  </h2>
                  <button
                    onClick={() => setShowKindPicker(false)}
                    className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
                    aria-label={t('accountModal.close')}
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-sm text-slate-500 mb-6 dark:text-gray-400">
                  {t('admin.kindPicker.subtitle')}
                </p>
                <div className="grid sm:grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => {
                      setContestForm((f) => ({ ...f, kind: 'output' }));
                      setShowKindPicker(false);
                      setShowForm(true);
                    }}
                    className="text-left p-5 rounded-xl border-2 border-gray-200 hover:border-violet-500 hover:bg-violet-500/5 transition-colors dark:border-slate-700 dark:hover:border-violet-400"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <FlaskConical className="w-5 h-5 text-violet-500 dark:text-violet-400" />
                      <h3 className="font-semibold text-slate-900 dark:text-white">
                        {t('admin.kindPicker.outputTitle')}
                      </h3>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-gray-400">
                      {t('admin.kindPicker.outputBody')}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-2 dark:text-gray-500">
                      {t('admin.kindPicker.outputExample')}
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setContestForm((f) => ({ ...f, kind: 'icpc' }));
                      setShowKindPicker(false);
                      setShowForm(true);
                    }}
                    className="text-left p-5 rounded-xl border-2 border-gray-200 hover:border-violet-500 hover:bg-violet-500/5 transition-colors dark:border-slate-700 dark:hover:border-violet-400"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Code className="w-5 h-5 text-violet-500 dark:text-violet-400" />
                      <h3 className="font-semibold text-slate-900 dark:text-white">
                        {t('admin.kindPicker.icpcTitle')}
                      </h3>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-gray-400">
                      {t('admin.kindPicker.icpcBody')}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-2 dark:text-gray-500">
                      {t('admin.kindPicker.icpcExample')}
                    </p>
                  </button>
                </div>
              </div>
            </div>
          )}

          {showForm && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto">
              <div className="glass-card p-6 w-full max-w-3xl my-8 animate-slide-up" role="dialog" aria-modal="true" aria-labelledby="contest-form-title">
                <div className="flex items-center justify-between mb-6">
                  <h2 id="contest-form-title" className="text-xl font-bold text-slate-900 dark:text-white">
                    {editContest ? t('admin.form.editTitle') : t('admin.form.createTitle')}
                  </h2>
                  <button
                    onClick={() => {
                      setShowForm(false);
                      setEditContest(null);
                    }}
                    className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
                    aria-label={t('admin.form.closeAria')}
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form onSubmit={handleContestSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">{t('admin.form.titleField')}</label>
                    <input
                      type="text"
                      className="input-field"
                      value={contestForm.title}
                      onChange={(e) => setContestForm({ ...contestForm, title: e.target.value })}
                      placeholder={t('admin.form.titlePlaceholder')}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">{t('admin.form.descriptionField')}</label>
                    <input
                      type="text"
                      className="input-field"
                      value={contestForm.description}
                      onChange={(e) => setContestForm({ ...contestForm, description: e.target.value })}
                      placeholder={t('admin.form.descriptionPlaceholder')}
                    />
                  </div>

                  {contestForm.kind !== 'icpc' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                      {t('admin.form.statementField')}
                    </label>
                    <textarea
                      className="input-field min-h-[200px] font-mono text-sm"
                      value={contestForm.problem_statement}
                      onChange={(e) => setContestForm({ ...contestForm, problem_statement: e.target.value })}
                      placeholder={t('admin.form.statementPlaceholder')}
                    />
                  </div>
                  )}

                  {!editContest && contestForm.kind !== 'icpc' && (
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 dark:bg-slate-800/30 dark:border-slate-700/40">
                      <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-2 dark:text-gray-300">
                        <FileType className="w-4 h-4 text-violet-500 dark:text-violet-400" />
                        {t('admin.form.pdfLabel')}
                      </label>
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        onChange={(e) => setCreatePdfFile(e.target.files?.[0] || null)}
                        className="input-field text-sm py-2 file:mr-2 file:py-0.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-violet-600 file:text-white"
                      />
                      {createPdfFile && (
                        <p className="text-xs text-slate-500 mt-1.5 dark:text-gray-500">
                          {createPdfFile.name}
                        </p>
                      )}
                      <p className="text-xs text-slate-500 mt-1.5 dark:text-gray-500">
                        {t('admin.form.pdfHint')}
                      </p>
                    </div>
                  )}

                  {editContest && contestForm.kind !== 'icpc' && (
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 dark:bg-slate-800/30 dark:border-slate-700/40">
                      <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-2 dark:text-gray-300">
                        <FileType className="w-4 h-4 text-violet-500 dark:text-violet-400" />
                        {t('admin.form.pdfLabel')}
                      </label>
                      {editContest.has_problem_statement_pdf ? (
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="w-4 h-4 text-violet-500 flex-shrink-0 dark:text-violet-400" />
                            <span className="text-sm text-slate-700 truncate dark:text-gray-200" title={editContest.problem_statement_pdf_name}>
                              {editContest.problem_statement_pdf_name || t('admin.form.pdfFilename')}
                            </span>
                          </div>
                          <div className="flex gap-2">
                            <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200">
                              <Upload className="w-3.5 h-3.5" />
                              {t('admin.form.replacePdf')}
                              <input
                                type="file"
                                accept="application/pdf,.pdf"
                                className="hidden"
                                onChange={handlePdfUpload}
                              />
                            </label>
                            <button
                              type="button"
                              onClick={handlePdfRemove}
                              className="text-xs font-medium px-3 py-1.5 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-600 transition-colors flex items-center gap-1.5 dark:text-red-400"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              {t('admin.form.removePdf')}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <label className="cursor-pointer inline-flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200">
                            <Upload className="w-4 h-4" />
                            {t('admin.form.uploadPdf')}
                            <input
                              type="file"
                              accept="application/pdf,.pdf"
                              className="hidden"
                              onChange={handlePdfUpload}
                            />
                          </label>
                          <p className="text-xs text-slate-500 mt-2 dark:text-gray-500">
                            {t('admin.form.pdfHint')}
                          </p>
                        </>
                      )}
                    </div>
                  )}

                  <div className="space-y-3">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                          {t('admin.form.visibleAt')}
                        </label>
                        <input
                          type="datetime-local"
                          className="input-field"
                          value={contestForm.visible_at}
                          onChange={(e) => setContestForm({ ...contestForm, visible_at: e.target.value })}
                        />
                        <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
                          {t('admin.form.visibleAtHint')}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                          {t('admin.form.startTime')}
                        </label>
                        <input
                          type="datetime-local"
                          className="input-field"
                          value={contestForm.start_time}
                          onChange={(e) => setContestForm({ ...contestForm, start_time: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                          {t('admin.form.endTime')}
                        </label>
                        <input
                          type="datetime-local"
                          className="input-field"
                          value={contestForm.end_time}
                          onChange={(e) => setContestForm({ ...contestForm, end_time: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                          {t('admin.form.hiddenAt')}
                        </label>
                        <input
                          type="datetime-local"
                          className="input-field"
                          value={contestForm.hidden_at}
                          onChange={(e) => setContestForm({ ...contestForm, hidden_at: e.target.value })}
                        />
                        <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
                          {t('admin.form.hiddenAtHint')}
                        </p>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                        {t('admin.form.freezeLabel')}
                      </label>
                      <input
                        type="datetime-local"
                        className="input-field"
                        value={contestForm.freeze_scoreboard_at}
                        onChange={(e) => setContestForm({ ...contestForm, freeze_scoreboard_at: e.target.value })}
                      />
                      <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
                        {t('admin.form.freezeHint')}
                      </p>
                    </div>
                  </div>

                  {contestForm.kind !== 'icpc' && (
                  <div>
                    <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                      <label className="block text-sm font-medium text-slate-700 dark:text-gray-300">
                        <Code className="w-4 h-4 inline mr-1" />
                        {t('admin.form.scriptLabel')}
                      </label>
                      <div className="flex gap-2">
                        <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200">
                          <Upload className="w-3.5 h-3.5" />
                          {t('admin.form.uploadPy')}
                          <input
                            type="file"
                            accept=".py,text/x-python,text/plain"
                            className="hidden"
                            onChange={handleScriptUpload}
                          />
                        </label>
                        <button
                          type="button"
                          onClick={handleScriptDownload}
                          disabled={!contestForm.scoring_script}
                          className="text-xs font-medium px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200"
                          title={t('admin.form.downloadPyTooltip')}
                        >
                          <FileDown className="w-3.5 h-3.5" />
                          {t('admin.form.downloadPy')}
                        </button>
                        {editContest && (
                          <button
                            type="button"
                            onClick={() => openTestScoring('score')}
                            className="text-xs font-medium px-3 py-1.5 rounded-md bg-violet-600/10 hover:bg-violet-600/20 border border-violet-500/30 text-violet-700 transition-colors flex items-center gap-1.5 dark:bg-violet-600/20 dark:hover:bg-violet-600/30 dark:text-violet-300"
                            title={t('admin.form.testScriptTooltip')}
                          >
                            <FlaskConical className="w-3.5 h-3.5" />
                            {t('admin.form.testScript')}
                          </button>
                        )}
                        {editContest && (
                          <button
                            type="button"
                            onClick={handleRescore}
                            disabled={rescoring}
                            className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300"
                            title={t('admin.form.rescoreTooltip')}
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${rescoring ? 'animate-spin' : ''}`} />
                            {rescoring ? t('admin.form.rescoring') : t('admin.form.rescoreAll')}
                          </button>
                        )}
                      </div>
                    </div>
                    <textarea
                      className="input-field min-h-[150px] font-mono text-sm"
                      value={contestForm.scoring_script}
                      onChange={(e) => setContestForm({ ...contestForm, scoring_script: e.target.value })}
                      placeholder={t('admin.form.scriptPlaceholder')}
                      spellCheck={false}
                    />
                    <p className="text-xs text-slate-500 mt-1.5 dark:text-gray-500">
                      {t('admin.form.scriptHint1', {
                        args: 'instance_data, submission_data',
                        score: 'score',
                      })}{' '}
                      {t('admin.form.scriptHint2', { mods: 'math, re, json' })}
                    </p>
                  </div>
                  )}

                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                        {t('admin.form.participationModeLabel')}
                      </label>
                      <select
                        className="input-field"
                        value={contestForm.participation_mode}
                        onChange={(e) => setContestForm({ ...contestForm, participation_mode: e.target.value })}
                      >
                        <option value="team">{t('admin.form.participationModeTeam')}</option>
                        <option value="solo">{t('admin.form.participationModeSolo')}</option>
                        <option value="both">{t('admin.form.participationModeBoth')}</option>
                      </select>
                      <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
                        {t('admin.form.participationModeHint')}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                        {t('admin.form.accessLabel')}
                      </label>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setContestForm({ ...contestForm, is_public: true })}
                          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                            contestForm.is_public
                              ? 'bg-violet-600 text-white border-violet-600'
                              : 'bg-white text-slate-700 border-gray-300 hover:bg-gray-100 dark:bg-slate-800 dark:text-gray-200 dark:border-slate-700 dark:hover:bg-slate-700'
                          }`}
                        >
                          <Globe className="w-4 h-4" />
                          {t('admin.form.accessPublic')}
                        </button>
                        <button
                          type="button"
                          onClick={() => setContestForm({ ...contestForm, is_public: false })}
                          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                            !contestForm.is_public
                              ? 'bg-violet-600 text-white border-violet-600'
                              : 'bg-white text-slate-700 border-gray-300 hover:bg-gray-100 dark:bg-slate-800 dark:text-gray-200 dark:border-slate-700 dark:hover:bg-slate-700'
                          }`}
                        >
                          <Lock className="w-4 h-4" />
                          {t('admin.form.accessPrivate')}
                        </button>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-600">
                        {contestForm.is_public
                          ? t('admin.form.accessPublicHint')
                          : t('admin.form.accessPrivateHint')}
                      </p>
                    </div>
                  </div>

                  {/* Kind is chosen in the picker modal. Show it as a
                      read-only badge here so the admin always sees which
                      kind of contest they're editing. */}
                  <div className="flex items-center gap-2 text-xs">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md font-medium ${
                      contestForm.kind === 'icpc'
                        ? 'bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300'
                        : 'bg-violet-500/15 text-violet-700 border border-violet-500/30 dark:text-violet-300'
                    }`}>
                      {contestForm.kind === 'icpc'
                        ? <><Code className="w-3.5 h-3.5" /> {t('admin.form.kindIcpc')}</>
                        : <><FlaskConical className="w-3.5 h-3.5" /> {t('admin.form.kindOutput')}</>
                      }
                    </span>
                    <span className="text-[11px] text-slate-400 dark:text-gray-500">
                      {contestForm.kind === 'icpc'
                        ? t('admin.form.kindIcpcHint')
                        : t('admin.form.kindOutputHint')}
                    </span>
                  </div>

                  {/* DOMjudge package importer — visible during create
                      (stages the file for post-create upload) and during
                      edit (imports immediately). */}
                  {contestForm.kind === 'icpc' && (
                    <div className="rounded-xl border-2 border-dashed border-sky-500/40 bg-sky-500/5 p-4">
                      <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2 dark:text-gray-300">
                        <Upload className="w-4 h-4 text-sky-500 dark:text-sky-400" />
                        {t('admin.form.importDomjudge')}
                      </label>
                      <input
                        type="file"
                        accept=".zip,application/zip"
                        onChange={async (e) => {
                          const f = e.target.files?.[0];
                          if (!f) return;
                          if (editContest) {
                            // Edit mode: import right away.
                            try {
                              const { data } = await importDomjudgePackage(editContest.id, f);
                              toast.success(t('admin.form.toastImportOk', {
                                problems: data.problems_imported,
                                testcases: data.testcases_imported,
                              }));
                            } catch (err) {
                              toast.error(err.response?.data?.detail || t('admin.form.toastImportFailed'));
                            } finally {
                              e.target.value = '';
                            }
                          } else {
                            // Create mode: stage the file; handleContestSubmit
                            // uploads it after the contest is created.
                            setCreateIcpcPackage(f);
                          }
                        }}
                        className="input-field text-sm py-2 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-sky-600 file:text-white"
                      />
                      {!editContest && createIcpcPackage && (
                        <p className="text-xs text-sky-700 mt-1.5 dark:text-sky-300">
                          {t('admin.form.icpcPackageStaged', { name: createIcpcPackage.name })}
                        </p>
                      )}
                      {!editContest && !createIcpcPackage && (
                        <p className="text-xs text-amber-700 mt-1.5 dark:text-amber-300">
                          {t('admin.form.icpcNoProblemsYet')}
                        </p>
                      )}
                      <p className="text-[11px] text-slate-500 mt-1.5 dark:text-gray-400">
                        {t('admin.form.importDomjudgeHint')}
                      </p>
                    </div>
                  )}

                  <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-gray-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={!!contestForm.practice_mode}
                      onChange={(e) => setContestForm({ ...contestForm, practice_mode: e.target.checked })}
                    />
                    <span>{t('admin.form.practiceMode')}</span>
                    <span className="text-[11px] text-slate-400 ml-1 dark:text-gray-500">
                      {t('admin.form.practiceModeHint')}
                    </span>
                  </label>

                  <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 dark:bg-slate-800/30 dark:border-slate-700/40">
                    <h4 className="text-sm font-semibold text-slate-700 dark:text-gray-300">
                      {t('admin.form.hardeningHeading')}
                    </h4>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!contestForm.dedup_block}
                        onChange={(e) => setContestForm({ ...contestForm, dedup_block: e.target.checked })}
                      />
                      <span>{t('admin.form.dedupBlock')}</span>
                      <span className="text-[11px] text-slate-400 ml-1 dark:text-gray-500">
                        {t('admin.form.dedupBlockHint')}
                      </span>
                    </label>
                    <div className={contestForm.kind === 'icpc' ? '' : 'grid sm:grid-cols-2 gap-3'}>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
                          {t('admin.form.cooldown')}
                        </label>
                        <input
                          type="number"
                          min={0}
                          className="input-field text-sm py-2"
                          value={contestForm.min_seconds_between_submits}
                          onChange={(e) => setContestForm({ ...contestForm, min_seconds_between_submits: e.target.value })}
                        />
                      </div>
                      {contestForm.kind !== 'icpc' && (
                        <div>
                          <label className="block text-xs font-medium text-slate-600 mb-1 dark:text-gray-400">
                            {t('admin.form.quota')}
                          </label>
                          <input
                            type="number"
                            min={0}
                            className="input-field text-sm py-2"
                            placeholder={t('admin.form.quotaPlaceholder')}
                            value={contestForm.max_submissions_per_instance}
                            onChange={(e) => setContestForm({ ...contestForm, max_submissions_per_instance: e.target.value })}
                          />
                        </div>
                      )}
                    </div>
                    {contestForm.kind !== 'icpc' && (
                      <div>
                        <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                          <label className="block text-xs font-medium text-slate-600 dark:text-gray-400">
                            {t('admin.form.validator')}
                          </label>
                          <div className="flex gap-2">
                            <label className="cursor-pointer text-xs font-medium px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200">
                              <Upload className="w-3.5 h-3.5" />
                              {t('admin.form.uploadPy')}
                              <input
                                type="file"
                                accept=".py,text/x-python,text/plain"
                                className="hidden"
                                onChange={handleValidatorUpload}
                              />
                            </label>
                            <button
                              type="button"
                              onClick={handleValidatorDownload}
                              disabled={!contestForm.output_validator_script}
                              className="text-xs font-medium px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200"
                              title={t('admin.form.downloadPyTooltip')}
                            >
                              <FileDown className="w-3.5 h-3.5" />
                              {t('admin.form.downloadPy')}
                            </button>
                            {editContest && (
                              <button
                                type="button"
                                onClick={() => openTestScoring('validate')}
                                disabled={!contestForm.output_validator_script}
                                className="text-xs font-medium px-3 py-1.5 rounded-md bg-violet-600/10 hover:bg-violet-600/20 border border-violet-500/30 text-violet-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-violet-600/20 dark:hover:bg-violet-600/30 dark:text-violet-300"
                                title={t('admin.form.testValidatorTooltip')}
                              >
                                <FlaskConical className="w-3.5 h-3.5" />
                                {t('admin.form.testScript')}
                              </button>
                            )}
                            {editContest && (
                              <button
                                type="button"
                                onClick={handleRescore}
                                disabled={rescoring}
                                className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300"
                                title={t('admin.form.rescoreTooltip')}
                              >
                                <RefreshCw className={`w-3.5 h-3.5 ${rescoring ? 'animate-spin' : ''}`} />
                                {rescoring ? t('admin.form.rescoring') : t('admin.form.rescoreAll')}
                              </button>
                            )}
                          </div>
                        </div>
                        <textarea
                          className="input-field text-xs font-mono min-h-[120px]"
                          placeholder={t('admin.form.validatorPlaceholder')}
                          value={contestForm.output_validator_script}
                          onChange={(e) => setContestForm({ ...contestForm, output_validator_script: e.target.value })}
                        />
                        <p className="text-[11px] text-slate-400 mt-1 dark:text-gray-500">
                          {t('admin.form.validatorHint')}
                        </p>
                      </div>
                    )}
                  </div>

                  {editContest && contestForm.kind !== 'icpc' && <AdminHints contestId={editContest.id} />}
                  {editContest && contestForm.kind === 'icpc' && (
                    // The `key` forces a remount when the admin jumps
                    // between different contests from the list — without
                    // it React reuses the same component instance and
                    // the inner state briefly shows the previous
                    // contest's problems under the new id.
                    <>
                      <IcpcProblemsPanel key={editContest.id} contestId={editContest.id} />
                      <IcpcStatsPanel key={`stats-${editContest.id}`} contestId={editContest.id} />
                    </>
                  )}

                  {editContest && !contestForm.is_public && (
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 dark:bg-slate-800/30 dark:border-slate-700/40">
                      <label className="block text-sm font-medium text-slate-700 flex items-center gap-2 dark:text-gray-300">
                        <Users className="w-4 h-4 text-violet-500 dark:text-violet-400" />
                        {t('admin.form.allowlistLabel')}
                        <span className="text-xs font-normal text-slate-400 dark:text-gray-500">
                          ({participants.length})
                        </span>
                      </label>

                      {(contestForm.participation_mode === 'team'
                        || contestForm.participation_mode === 'both') && (
                        <div className="flex gap-2">
                          <select
                            className="input-field text-sm py-2 flex-1"
                            value={participantTeamId}
                            onChange={(e) => setParticipantTeamId(e.target.value)}
                          >
                            <option value="">{t('admin.form.allowlistPickTeam')}</option>
                            {allTeams
                              .filter((tm) => !participants.some((p) => p.kind === 'team' && p.team_id === tm.id))
                              .map((tm) => (
                                <option key={tm.id} value={tm.id}>
                                  {tm.name}
                                </option>
                              ))}
                          </select>
                          <button
                            type="button"
                            onClick={handleAddParticipantTeam}
                            disabled={!participantTeamId}
                            className="btn-primary text-sm py-2 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <UserPlus className="w-4 h-4 mr-1 inline" />
                            {t('admin.form.allowlistAddTeam')}
                          </button>
                        </div>
                      )}

                      {(contestForm.participation_mode === 'solo'
                        || contestForm.participation_mode === 'both') && (
                        <div className="flex gap-2">
                          <select
                            className="input-field text-sm py-2 flex-1"
                            value={participantUserId}
                            onChange={(e) => setParticipantUserId(e.target.value)}
                          >
                            <option value="">{t('admin.form.allowlistPickUser')}</option>
                            {users
                              .filter((u) => !participants.some((p) => p.kind === 'user' && p.user_id === u.id))
                              .map((u) => (
                                <option key={u.id} value={u.id}>
                                  {u.username} ({u.email})
                                </option>
                              ))}
                          </select>
                          <button
                            type="button"
                            onClick={handleAddParticipantUser}
                            disabled={!participantUserId}
                            className="btn-primary text-sm py-2 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <UserPlus className="w-4 h-4 mr-1 inline" />
                            {t('admin.form.allowlistAddUser')}
                          </button>
                        </div>
                      )}

                      {participants.length === 0 ? (
                        <p className="text-xs text-slate-400 italic dark:text-gray-600">
                          {t('admin.form.allowlistEmpty')}
                        </p>
                      ) : (
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                          {participants.map((p) => (
                            <div
                              key={p.id}
                              className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-white border border-gray-200 dark:bg-slate-700/20 dark:border-transparent"
                            >
                              <div className="text-sm text-slate-700 dark:text-gray-200">
                                {p.kind === 'team' ? (
                                  <span className="font-medium">
                                    <Users className="w-3.5 h-3.5 inline mr-1 text-violet-500" />
                                    {p.team_name}
                                    <span className="text-xs text-slate-400 ml-2 dark:text-gray-500">
                                      ({t('admin.form.allowlistTeamBadge')})
                                    </span>
                                  </span>
                                ) : (
                                  <>
                                    <span className="font-medium">{p.username}</span>
                                    <span className="text-xs text-slate-400 ml-2 dark:text-gray-500">
                                      {p.email}
                                    </span>
                                  </>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemoveParticipant(p.id)}
                                className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors dark:text-gray-500 dark:hover:text-red-400"
                                title={t('admin.form.allowlistRemove')}
                              >
                                <UserMinus className="w-4 h-4" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowForm(false);
                        setEditContest(null);
                      }}
                      className="btn-secondary"
                    >
                      {t('common.cancel')}
                    </button>
                    <button type="submit" className="btn-primary">
                      <Save className="w-4 h-4 mr-2 inline" />
                      {editContest ? t('admin.form.saveUpdate') : t('admin.form.saveCreate')}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {contests.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Trophy className="w-14 h-14 text-slate-300 mx-auto mb-4 dark:text-gray-600" />
              <h3 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">{t('admin.contests.noneHeading')}</h3>
              <p className="text-slate-500 dark:text-gray-400">{t('admin.contests.noneBody')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {contests.map((c) => (
                <div key={c.id} className="glass-card p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">{c.title}</h3>
                        <span className={c.is_active ? 'badge-active' : 'badge-inactive'}>
                          {c.is_active ? t('admin.contests.active') : t('admin.contests.inactive')}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                          c.kind === 'icpc'
                            ? 'bg-sky-500/15 text-sky-700 border-sky-500/30 dark:text-sky-300'
                            : 'bg-violet-500/15 text-violet-700 border-violet-500/30 dark:text-violet-300'
                        }`}>
                          {c.kind === 'icpc'
                            ? <><Code className="w-3 h-3" /> ICPC</>
                            : <><FlaskConical className="w-3 h-3" /> {t('admin.form.kindOutput').split(' ')[0]}</>
                          }
                        </span>
                      </div>
                      <p className="text-slate-500 text-sm dark:text-gray-400">{c.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/scoreboard/${c.id}`}
                        className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-violet-500 transition-colors dark:hover:bg-slate-700/50 dark:text-gray-400 dark:hover:text-violet-400"
                        title={t('admin.contests.viewBoard')}
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={async () => {
                          try {
                            await updateContest(c.id, { is_active: !c.is_active });
                            toast.success(c.is_active ? t('admin.contests.toastPaused') : t('admin.contests.toastResumed'));
                            refresh();
                          } catch (err) {
                            toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
                          }
                        }}
                        className={`p-2 rounded-lg transition-colors ${
                          c.is_active
                            ? 'hover:bg-amber-500/10 text-slate-400 hover:text-amber-500 dark:text-gray-400 dark:hover:text-amber-400'
                            : 'hover:bg-emerald-500/10 text-slate-400 hover:text-emerald-500 dark:text-gray-400 dark:hover:text-emerald-400'
                        }`}
                        title={c.is_active ? t('admin.contests.pause') : t('admin.contests.resume')}
                      >
                        {c.is_active
                          ? <Pause className="w-4 h-4" />
                          : <Play className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => startEdit(c)}
                        className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-violet-500 transition-colors dark:hover:bg-slate-700/50 dark:text-gray-400 dark:hover:text-violet-400"
                        title={t('admin.contests.edit')}
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await duplicateContest(c.id);
                            toast.success(t('admin.contests.duplicated'));
                            refresh();
                          } catch (err) {
                            toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
                          }
                        }}
                        className="p-2 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-violet-500 transition-colors dark:hover:bg-slate-700/50 dark:text-gray-400 dark:hover:text-violet-400"
                        title={t('admin.contests.duplicate')}
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteContest(c.id, c.title)}
                        className="p-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors dark:text-gray-400 dark:hover:text-red-400"
                        title={t('admin.contests.delete')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {c.kind === 'icpc' ? (
                    <div className="bg-gray-50 rounded-xl p-4 text-sm text-slate-500 dark:bg-slate-800/30 dark:text-gray-400">
                      {t('admin.contests.icpcEditHint')}
                    </div>
                  ) : (
                  <div className="bg-gray-50 rounded-xl p-4 dark:bg-slate-800/30">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2 dark:text-gray-300">
                      <Target className="w-4 h-4 text-violet-500 dark:text-violet-400" />
                      {t('admin.contests.instancesHeading', { count: c.instances?.length || 0 })}
                    </h4>

                    {c.instances?.length > 0 && (
                      <div className="space-y-2 mb-3">
                        {c.instances.map((inst) => (
                          <div
                            key={inst.id}
                            className="flex items-center justify-between py-2 px-3 rounded-lg bg-white border border-gray-200 dark:bg-slate-700/20 dark:border-transparent"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <FileText className="w-4 h-4 text-violet-500 flex-shrink-0 dark:text-violet-400" />
                              <span className="text-sm text-slate-700 truncate dark:text-gray-200">{inst.name}</span>
                              {inst.unlock_delay_seconds > 0 && (
                                <span
                                  className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-400"
                                  title={inst.unlock_at ? t('admin.instance.unlocksAt', { at: formatDateTime(inst.unlock_at) }) : undefined}
                                >
                                  +{Math.round(inst.unlock_delay_seconds / 60)} min
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              <button
                                onClick={() => setEditingInstance(inst)}
                                className="p-1 rounded hover:bg-violet-500/10 text-slate-400 hover:text-violet-500 transition-colors dark:text-gray-500 dark:hover:text-violet-400"
                                title={t('admin.contests.editInstance')}
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteInstance(inst.id)}
                                className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors dark:text-gray-500 dark:hover:text-red-400"
                                title={t('admin.contests.deleteInstance')}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex flex-wrap gap-3 items-end">
                      <div className="flex-1 min-w-[150px]">
                        <input
                          type="text"
                          className="input-field text-sm py-2"
                          placeholder={t('admin.contests.instanceNamePlaceholder')}
                          value={instanceForm.name}
                          onChange={(e) => setInstanceForm({ ...instanceForm, name: e.target.value })}
                        />
                      </div>
                      <div className="flex items-end gap-2">
                        <div className="w-28">
                          <select
                            className="input-field text-sm py-2"
                            value={instanceForm.unlock_mode}
                            onChange={(e) =>
                              setInstanceForm({ ...instanceForm, unlock_mode: e.target.value })
                            }
                            title={t('admin.instance.unlockModeHint')}
                          >
                            <option value="relative">{t('admin.instance.unlockRelative')}</option>
                            <option value="absolute">{t('admin.instance.unlockAbsolute')}</option>
                          </select>
                        </div>
                        {instanceForm.unlock_mode === 'absolute' ? (
                          <div className="w-48">
                            <input
                              type="datetime-local"
                              className="input-field text-sm py-2"
                              value={instanceForm.unlock_at_absolute}
                              onChange={(e) =>
                                setInstanceForm({ ...instanceForm, unlock_at_absolute: e.target.value })
                              }
                              title={t('admin.instance.unlockAbsoluteHint')}
                            />
                          </div>
                        ) : (
                          <div className="w-28">
                            <input
                              type="number"
                              min={0}
                              step={1}
                              className="input-field text-sm py-2"
                              placeholder={t('admin.contests.unlockDelayPlaceholder')}
                              value={instanceForm.unlock_delay_minutes}
                              onChange={(e) =>
                                setInstanceForm({ ...instanceForm, unlock_delay_minutes: e.target.value })
                              }
                              title={t('admin.contests.unlockDelayTitle')}
                            />
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-[150px]">
                        <input
                          type="file"
                          onChange={(e) => setInstanceFile(e.target.files[0])}
                          className="input-field text-sm py-2 file:mr-2 file:py-0.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-violet-600 file:text-white"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleAddInstance(c.id)}
                        className="btn-primary text-sm py-2"
                      >
                        <Upload className="w-4 h-4 mr-1 inline" />
                        {t('admin.contests.addInstance')}
                      </button>
                    </div>

                    {(!c.instances || c.instances.length === 0) && (
                      <p className="text-slate-400 text-sm text-center py-2 mt-2 dark:text-gray-600">
                        {t('admin.contests.noInstancesYet')}
                      </p>
                    )}
                  </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'submissions' && <SubmissionsTab contests={contests} />}
      {tab === 'packages' && <PackagesPanel />}

      {tab === 'scoring' && <ScoringPanel />}

      {tab === 'audit' && <AuditLogTab />}

      {editingInstance && (
        <EditInstanceModal
          instance={editingInstance}
          onClose={() => setEditingInstance(null)}
          onSaved={() => { setEditingInstance(null); refresh(); }}
        />
      )}

      {testScoringOpen && editContest && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="glass-card p-6 w-full max-w-2xl my-8 animate-slide-up" role="dialog" aria-modal="true">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
                <FlaskConical className="w-5 h-5 text-violet-500 dark:text-violet-400" />
                {testScoringState.mode === 'validate'
                  ? t('admin.testScoring.titleValidate')
                  : t('admin.testScoring.title')}
              </h2>
              <button
                onClick={() => setTestScoringOpen(false)}
                className="p-1 rounded-lg hover:bg-gray-100 text-slate-400 hover:text-slate-900 transition-colors dark:hover:bg-slate-800 dark:text-gray-400 dark:hover:text-white"
                aria-label="Fermer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={runTestScoring} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">{t('admin.testScoring.instanceLabel')}</label>
                <select
                  className="input-field"
                  value={testScoringState.instance_id}
                  onChange={(e) => setTestScoringState((s) => ({ ...s, instance_id: e.target.value }))}
                  required
                >
                  <option value="">{t('admin.testScoring.instancePlaceholder')}</option>
                  {(editContest.instances || []).map((inst) => (
                    <option key={inst.id} value={inst.id}>{inst.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                  {t('admin.testScoring.submissionLabel')}
                </label>
                <textarea
                  className="input-field font-mono text-xs min-h-[160px]"
                  placeholder={t('admin.testScoring.submissionPlaceholder')}
                  value={testScoringState.submission_data}
                  onChange={(e) => setTestScoringState((s) => ({ ...s, submission_data: e.target.value }))}
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={testScoringState.useOverride}
                  onChange={(e) => setTestScoringState((s) => ({ ...s, useOverride: e.target.checked }))}
                />
                {t('admin.testScoring.useEditorScript')}
              </label>

              {testScoringState.result && (
                <div
                  className={`rounded-xl p-3 border ${
                    testScoringState.result.ok
                      ? 'border-emerald-500/30 bg-emerald-500/10'
                      : 'border-red-500/30 bg-red-500/10'
                  }`}
                >
                  {testScoringState.result.ok ? (
                    <p className="text-sm text-emerald-700 dark:text-emerald-300">
                      {testScoringState.mode === 'validate' ? (
                        <>
                          <span className="font-semibold">{t('admin.testScoring.validOk')}</span>
                        </>
                      ) : (
                        <>
                          <span className="font-semibold">{t('admin.testScoring.scoreLabel')}</span>{' '}
                          <span className="font-mono">{testScoringState.result.score}</span>
                        </>
                      )}
                      <span className="text-xs text-slate-500 ml-3 dark:text-gray-400">
                        ({testScoringState.result.duration_ms} ms)
                      </span>
                    </p>
                  ) : (
                    <p className="text-sm text-red-700 dark:text-red-300">
                      <span className="font-semibold">
                        {testScoringState.mode === 'validate'
                          ? t('admin.testScoring.invalidLabel')
                          : t('admin.testScoring.errorLabel')}
                      </span>{' '}
                      <span className="font-mono break-all">{testScoringState.result.error}</span>
                    </p>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setTestScoringOpen(false)} className="btn-secondary text-sm">
                  {t('admin.testScoring.closeBtn')}
                </button>
                <button type="submit" className="btn-primary text-sm" disabled={testScoringState.running}>
                  {testScoringState.running ? t('admin.testScoring.running') : t('admin.testScoring.run')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
