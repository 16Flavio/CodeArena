import { useState, useEffect, Fragment } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  getContest, getMyTeams, downloadInstance, submitSolution, submitSolutionCode,
  listIcpcLanguages, getSubmissions,
  downloadProblemStatement, listAnnouncements, createAnnouncement, deleteAnnouncement,
  getMyContestRegistration, registerToContest, unregisterFromContest,
  listContestRegistrations, downloadMySubmission,
  setRegistrationDisqualified,
} from '../api';
import { useAuth } from '../AuthContext';
import ReactMarkdown from 'react-markdown';
import {
  FileDown, Upload, Trophy, Clock, Target, CheckCircle, XCircle,
  AlertCircle, ChevronDown, ChevronUp, ArrowRight, FileType, ExternalLink, Lock,
  Megaphone, FileText as FileTextIcon, Code2, Users, Link2, Ban,
} from 'lucide-react';
import { copyText } from '../utils/clipboard';
import { useConfirm, usePrompt } from '../components/Confirm';
import HintsPanel from '../components/HintsPanel';
import IcpcContestView from '../components/IcpcContestView';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import { useTheme } from '../ThemeContext';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { formatScore, formatScoreFull } from '../utils/format';
import { formatCountdown, formatDateTime, backendIsoMs } from '../utils/datetime';

const SUBMISSION_PAGE_SIZE = 25;

export default function ContestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const confirm = useConfirm();
  const prompt = usePrompt();
  const { t } = useTranslation();
  const { theme } = useTheme();
  const [annForm, setAnnForm] = useState({ title: '', body: '' });
  const [annSubmitting, setAnnSubmitting] = useState(false);
  const [contest, setContest] = useState(null);
  const [teams, setTeams] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [submissionsTotal, setSubmissionsTotal] = useState(0);
  const [submissionPage, setSubmissionPage] = useState(0);
  const [announcements, setAnnouncements] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  // Submission id whose error detail row is expanded, or null.
  const [expandedErrorId, setExpandedErrorId] = useState(null);
  const [submitKind, setSubmitKind] = useState('team'); // 'team' | 'solo' — only relevant when mode is 'both'
  const [selectedInstance, setSelectedInstance] = useState('');
  const [file, setFile] = useState(null);
  const [submitMode, setSubmitMode] = useState('file'); // 'file' | 'code' | 'source'
  const [codeText, setCodeText] = useState('');
  // For submitMode === 'source', the server will compile + run this code.
  const [sourceLanguage, setSourceLanguage] = useState('py3');
  const [sourceLanguages, setSourceLanguages] = useState([]);
  useEffect(() => {
    // Languages come from the ICPC-side endpoint (it's the canonical
    // list of what the judging pipeline supports).
    listIcpcLanguages().then((r) => setSourceLanguages(r.data || [])).catch(() => {});
  }, []);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showStatement, setShowStatement] = useState(true);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [pdfRetryCount, setPdfRetryCount] = useState(0);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [registration, setRegistration] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [participants, setParticipants] = useState([]);
  const [showParticipants, setShowParticipants] = useState(false);

  // Tick once a second so "unlocks in X" / "ends in X" stay live without
  // re-fetching the whole contest.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const refreshRegistration = async (contestId) => {
    try {
      const { data } = await getMyContestRegistration(contestId);
      setRegistration(data);
    } catch {
      setRegistration(null);
    }
  };

  const refreshParticipants = async (contestId) => {
    try {
      const { data } = await listContestRegistrations(contestId);
      setParticipants(data);
    } catch {
      setParticipants([]);
    }
  };

  useEffect(() => {
    Promise.all([
      getContest(id),
      getMyTeams(),
      getMyContestRegistration(id).catch(() => ({ data: null })),
      listContestRegistrations(id).catch(() => ({ data: [] })),
    ])
      .then(([c, t, r, p]) => {
        setContest(c.data);
        setTeams(t.data);
        setRegistration(r.data);
        setParticipants(p.data || []);
        if (t.data.length > 0) setSelectedTeam(t.data[0].id);
        const mode = c.data?.participation_mode || 'team';
        if (mode === 'solo') setSubmitKind('solo');
        else if (mode === 'team') setSubmitKind('team');
        else setSubmitKind(t.data.length > 0 ? 'team' : 'solo');
      })
      .catch(() => toast.error(t('contest.toastLoadFailed')))
      .finally(() => setLoading(false));
  }, [id]);

  const handleRegister = async (kindOverride = null) => {
    // ``kindOverride`` is "solo" | "team" for the explicit buttons used
    // in "both" mode; omitted when the contest is pure solo or pure
    // team (the backend infers the right path from participation_mode).
    setRegistering(true);
    try {
      let payload = {};
      if (kindOverride === 'team') {
        if (!selectedTeam) {
          toast.error(t('contest.toastSelectTeam'));
          return;
        }
        payload = { team_id: selectedTeam };
      } else if (kindOverride === 'solo') {
        payload = {};   // no team_id → solo registration
      }
      await registerToContest(contest.id, payload);
      toast.success(t('contest.toastRegistered'));
      // Re-fetch the bits that changed instead of reloading the whole
      // SPA — keeps scroll, route, and unrelated state intact.
      await Promise.all([
        refreshRegistration(contest.id),
        refreshParticipants(contest.id),
      ]);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('contest.toastRegisterFailed'));
    } finally {
      setRegistering(false);
    }
  };

  const handleUnregister = async () => {
    const ok = await confirm({
      message: t('contest.confirmUnregister'),
      danger: true,
    });
    if (!ok) return;
    setRegistering(true);
    try {
      await unregisterFromContest(contest.id);
      toast.success(t('contest.toastUnregistered'));
      // Submissions + registration are now gone — bounce to the
      // dashboard so the user doesn't sit on a contest page they
      // can't participate in anymore (the problems list would go
      // empty, the submit form would 403 on every attempt, etc.).
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || t('contest.toastUnregisterFailed'));
    } finally {
      setRegistering(false);
    }
  };

  useEffect(() => {
    if (contest) {
      getSubmissions(contest.id, selectedTeam || null, SUBMISSION_PAGE_SIZE, submissionPage * SUBMISSION_PAGE_SIZE)
        .then((r) => {
          setSubmissions(r.data.items || []);
          setSubmissionsTotal(r.data.total || 0);
        })
        .catch(() => {});
    }
  }, [selectedTeam, contest, submissionPage]);

  useEffect(() => {
    if (contest) {
      listAnnouncements(contest.id)
        .then((r) => setAnnouncements(r.data))
        .catch(() => {});
    }
  }, [contest?.id]);

  const refreshAnnouncements = async () => {
    try {
      const r = await listAnnouncements(contest.id);
      setAnnouncements(r.data);
    } catch {
      /* ignore */
    }
  };

  const handleCreateAnnouncement = async (e) => {
    e.preventDefault();
    if (!annForm.body.trim()) return;
    setAnnSubmitting(true);
    try {
      await createAnnouncement(contest.id, annForm);
      toast.success(t('contest.toastAnnouncePublished'));
      setAnnForm({ title: '', body: '' });
      refreshAnnouncements();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('contest.toastAnnounceFailed'));
    } finally {
      setAnnSubmitting(false);
    }
  };

  const handleDeleteAnnouncement = async (id) => {
    const ok = await confirm({
      message: t('contest.confirmDeleteAnn'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteAnnouncement(id);
      refreshAnnouncements();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
    }
  };

  useEffect(() => {
    if (!contest?.has_problem_statement_pdf) {
      setPdfBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      return undefined;
    }
    let cancelled = false;
    let createdUrl = null;
    setPdfLoading(true);
    downloadProblemStatement(contest.id)
      .then((r) => {
        if (cancelled) return;
        createdUrl = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
        setPdfBlobUrl(createdUrl);
      })
      .catch(async (err) => {
        if (cancelled) return;
        // 403 = registration or pre-start gate; surface the backend's
        // French message instead of the generic "pdf load failed".
        let msg = t('contest.pdfLoadFailed');
        try {
          if (err.response?.data instanceof Blob) {
            const text = await err.response.data.text();
            const parsed = JSON.parse(text);
            if (parsed?.detail) msg = parsed.detail;
          } else if (err.response?.data?.detail) {
            msg = err.response.data.detail;
          }
        } catch { /* keep the generic message */ }
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setPdfLoading(false);
      });
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [contest?.id, contest?.has_problem_statement_pdf, pdfRetryCount]);

  const handleDownload = async (instanceId, instanceName) => {
    try {
      const res = await downloadInstance(instanceId);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = res.headers['content-disposition']
        ? res.headers['content-disposition'].split('filename=')[1]?.replace(/"/g, '')
        : `${instanceName}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t('contest.toastDownloadFailed'));
    }
  };

  const pollSubmissionStatus = async (submissionId) => {
    // Poll until the async scoring settles (max ~30s).
    for (let i = 0; i < 60; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((res) => setTimeout(res, 500));
      try {
        // eslint-disable-next-line no-await-in-loop
        const { data } = await (await import('../api')).getSubmission(submissionId);
        if (data.status !== 'pending') return data;
      } catch {
        // keep polling briefly
      }
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedInstance) {
      toast.error(t('contest.toastSelectFields'));
      return;
    }
    if (submitKind === 'team' && !selectedTeam) {
      toast.error(t('contest.toastSelectFields'));
      return;
    }
    let blob;
    let fileName;
    if (submitMode === 'file') {
      if (!file) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
      blob = file;
      fileName = file.name;
    } else if (submitMode === 'source') {
      if (!codeText.trim()) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
    } else {
      const text = codeText;
      if (!text.trim()) {
        toast.error(t('contest.toastSelectFields'));
        return;
      }
      blob = new Blob([text], { type: 'text/plain' });
      fileName = 'submission.py';
    }
    setUploading(true);
    try {
      const formData = new FormData();
      if (submitMode === 'source') {
        // Compile+run path: server runs the program, captures stdout,
        // and feeds THAT to the validator + scorer.
        formData.append('language', sourceLanguage);
        formData.append('source', codeText);
      } else {
        formData.append('file', blob, fileName);
      }
      if (submitKind === 'team') {
        formData.append('team_id', selectedTeam);
      }
      const submitFn = submitMode === 'source' ? submitSolutionCode : submitSolution;
      const { data } = await submitFn(contest.id, selectedInstance, formData);
      toast.loading(t('contest.scoringInProgress'), { id: `sub-${data.id}` });
      const final = await pollSubmissionStatus(data.id);
      toast.dismiss(`sub-${data.id}`);
      if (!final) {
        toast.error(t('contest.scoringTakingLong'));
      } else if (final.status === 'scored') {
        toast.success(t('contest.toastScoreFormat', { score: formatScore(final.score) }));
      } else {
        const msg = (final.error_message || t('contest.toastUnknownError')).slice(0, 160);
        toast.error(t('contest.toastScoringError', { msg }));
      }
      setFile(null);
      setCodeText('');
      setSubmissionPage(0);
      const r = await getSubmissions(contest.id, selectedTeam || null, SUBMISSION_PAGE_SIZE, 0);
      setSubmissions(r.data.items || []);
      setSubmissionsTotal(r.data.total || 0);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('contest.toastSubmitFailed'));
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isBanned = Boolean(registration?.disqualified) && !user?.is_admin;
  const canParticipate = Boolean(user?.is_admin || (registration?.registered && !isBanned));

  if (!contest) {
    return (
      <div className="glass-card p-12 text-center">
        <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4 dark:text-amber-400" />
        <h3 className="text-xl font-bold text-slate-900 mb-2 dark:text-white">{t('contest.notFoundHeading')}</h3>
        <p className="text-slate-500 mb-4 dark:text-gray-400">{t('contest.notFoundBody')}</p>
        <Link to="/dashboard" className="btn-primary text-sm inline-block">
          {t('contest.backToDashboard')}
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <h1 className="text-3xl font-bold text-slate-900 break-words dark:text-white">{contest.title}</h1>
            {contest.is_open_for_submissions ? (
              <span className="badge-active">{t('contest.statusLive')}</span>
            ) : contest.end_time && backendIsoMs(contest.end_time) <= now ? (
              <span className="badge-inactive">{t('contest.statusEnded')}</span>
            ) : contest.start_time && backendIsoMs(contest.start_time) > now ? (
              <span className="badge bg-sky-500/15 text-sky-700 border border-sky-500/30 dark:text-sky-300">
                {t('contest.statusUpcoming')}
              </span>
            ) : (
              <span className="badge-inactive">{t('contest.statusClosed')}</span>
            )}
          </div>
          <p className="text-slate-500 dark:text-gray-400">{contest.description}</p>
          <div className="text-xs text-slate-400 mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 dark:text-gray-500">
            {contest.start_time && (
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {t('contest.startLabel')} {formatDateTime(contest.start_time)}
              </span>
            )}
            {contest.end_time && (
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {t('contest.endLabel')} {formatDateTime(contest.end_time)}
                {backendIsoMs(contest.end_time) > now && (
                  <span className="text-slate-500 dark:text-gray-400">
                    {t('contest.endingIn', {
                      remaining: formatCountdown((backendIsoMs(contest.end_time) - now) / 1000),
                    })}
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={async () => {
              const ok = await copyText(window.location.href);
              if (ok) toast.success(t('contest.toastLinkCopied'));
              else toast.error(t('contest.toastLinkCopyFailed'));
            }}
            className="btn-secondary text-sm"
            title={t('contest.copyLink')}
          >
            <Link2 className="w-4 h-4 mr-2 inline" />
            {t('contest.copyLink')}
          </button>
          <Link to={`/scoreboard/${contest.id}`} className="btn-secondary text-sm">
            <Trophy className="w-4 h-4 mr-2 inline" />
            {t('contest.scoreboard')}
          </Link>
        </div>
      </div>

      {(announcements.length > 0 || user?.is_admin) && (
        <div className="glass-card p-5 border border-sky-500/30 bg-sky-500/5">
          <h2 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2 dark:text-white">
            <Megaphone className="w-5 h-5 text-sky-600 dark:text-sky-400" />
            {t('contest.announcements')}
          </h2>
          {user?.is_admin && (
            <form onSubmit={handleCreateAnnouncement} className="space-y-2 mb-4 p-3 rounded-xl bg-white/70 border border-sky-500/20 dark:bg-slate-900/50">
              <input
                type="text"
                className="input-field text-sm py-2"
                placeholder={t('contest.annTitleOptional')}
                value={annForm.title}
                onChange={(e) => setAnnForm({ ...annForm, title: e.target.value })}
                maxLength={200}
              />
              <textarea
                className="input-field text-sm py-2 min-h-[80px]"
                placeholder={t('contest.annBodyPlaceholder')}
                value={annForm.body}
                onChange={(e) => setAnnForm({ ...annForm, body: e.target.value })}
                required
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="btn-primary text-sm py-1.5 px-4"
                  disabled={annSubmitting || !annForm.body.trim()}
                >
                  {annSubmitting ? t('contest.publishing') : t('contest.publish')}
                </button>
              </div>
            </form>
          )}
          {announcements.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-gray-400">{t('contest.noAnnouncements')}</p>
          ) : (
            <div className="space-y-3">
              {announcements.map((a) => (
                <div key={a.id} className="rounded-xl p-3 bg-white/70 border border-sky-500/20 flex items-start justify-between gap-3 dark:bg-slate-900/50">
                  <div className="min-w-0 flex-1">
                    {a.title && (
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">{a.title}</p>
                    )}
                    <p className="text-sm text-slate-700 whitespace-pre-wrap mt-1 dark:text-gray-200">{a.body}</p>
                    <p className="text-[11px] text-slate-500 mt-2 dark:text-gray-500">
                      {a.author_username ? `${a.author_username} · ` : ''}
                      {formatDateTime(a.created_at)}
                    </p>{/* */}
                  </div>
                  {user?.is_admin && (
                    <button
                      onClick={() => handleDeleteAnnouncement(a.id)}
                      className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors flex-shrink-0 dark:text-gray-500 dark:hover:text-red-400"
                      title={t('common.delete')}
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {canParticipate && contest.kind !== 'icpc' && <HintsPanel contestId={contest.id} />}

      {contest.kind === 'icpc' && (
        <IcpcContestView
          contest={contest}
          canParticipate={canParticipate}
          // Solo contests must submit without a team_id, even if the
          // user happens to be in one. "both" contests follow the
          // user's explicit submitKind choice.
          selectedTeamId={
            contest.participation_mode === 'solo'
              ? null
              : contest.participation_mode === 'both'
                ? (submitKind === 'solo' ? null : (selectedTeam || null))
                : (selectedTeam || null)
          }
        />
      )}

      {contest.kind !== 'icpc' && canParticipate && (
      <div className="glass-card overflow-hidden">
        <button
          onClick={() => setShowStatement(!showStatement)}
          className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors dark:hover:bg-slate-800/30"
        >
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            {contest.has_problem_statement_pdf ? (
              <FileType className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            ) : (
              <Target className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            )}
            {t('contest.problemStatement')}
            {contest.has_problem_statement_pdf && (
              <span className="text-xs font-normal text-slate-400 ml-1 dark:text-gray-500">{t('contest.pdfBadge')}</span>
            )}
          </h2>
          <div className="flex items-center gap-2">
            {contest.has_problem_statement_pdf && pdfBlobUrl && (
              <a
                href={pdfBlobUrl}
                download={contest.problem_statement_pdf_name || 'enonce.pdf'}
                onClick={(e) => e.stopPropagation()}
                className="text-xs font-medium px-2.5 py-1 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200"
                title={t('common.download')}
              >
                <FileDown className="w-3.5 h-3.5" />
                {t('common.download')}
              </a>
            )}
            {contest.has_problem_statement_pdf && pdfBlobUrl && (
              <a
                href={pdfBlobUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-xs font-medium px-2.5 py-1 rounded-md bg-gray-100 hover:bg-gray-200 border border-gray-300 text-slate-700 transition-colors flex items-center gap-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-gray-200"
                title={t('common.openInNewTab')}
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {t('common.openInNewTab')}
              </a>
            )}
            {showStatement ? (
              <ChevronUp className="w-5 h-5 text-slate-400 dark:text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400 dark:text-gray-400" />
            )}
          </div>
        </button>
        {showStatement && (
          contest.has_problem_statement_pdf ? (
            <div className="px-6 pb-6">
              {pdfLoading && !pdfBlobUrl ? (
                <div className="flex items-center justify-center h-96 bg-gray-100 rounded-xl dark:bg-slate-950/40">
                  <div className="w-6 h-6 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : pdfBlobUrl ? (
                <iframe
                  src={pdfBlobUrl}
                  title={t('contest.problemStatement')}
                  className="w-full rounded-xl border border-gray-200 bg-white dark:border-slate-800"
                  style={{ height: '75vh', minHeight: 480 }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-slate-500 gap-3 dark:text-gray-400">
                  <AlertCircle className="w-8 h-8 text-amber-500 dark:text-amber-400" />
                  <p>{t('contest.pdfLoadFailed')}</p>
                  <button onClick={() => setPdfRetryCount((n) => n + 1)} className="btn-secondary text-sm">
                    {t('common.retry')}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="px-6 pb-6 prose prose-slate max-w-none dark:prose-invert dark:prose-violet">
              <ReactMarkdown>{contest.problem_statement || t('contest.noStatement')}</ReactMarkdown>
            </div>
          )
        )}
      </div>
      )}

      {canParticipate && contest.kind !== 'icpc' && (
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2 dark:text-white">
          <FileDown className="w-5 h-5 text-violet-500 dark:text-violet-400" />
          {t('contest.instances')}
        </h2>
        {contest.instances.length === 0 ? (
          <p className="text-slate-500 text-center py-4 dark:text-gray-500">{t('contest.noInstances')}</p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {contest.instances.map((inst) => {
              const unlockMs = backendIsoMs(inst.unlock_at);
              const locked = !inst.is_unlocked;
              return (
                <div
                  key={inst.id}
                  className={`flex items-center justify-between p-4 rounded-xl border ${
                    locked
                      ? 'bg-amber-500/5 border-amber-500/20'
                      : 'bg-gray-50 border-gray-200 dark:bg-slate-800/30 dark:border-slate-700/30'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 min-w-0">
                      {locked && <Lock className="w-4 h-4 text-amber-500 flex-shrink-0 dark:text-amber-400" />}
                      <p className={`font-medium truncate ${locked ? 'text-slate-600 dark:text-gray-400' : 'text-slate-900 dark:text-white'}`}>
                        {inst.name}
                      </p>
                    </div>
                    {locked && unlockMs && (
                      <p className="text-xs text-amber-700 mt-1 dark:text-amber-300">
                        {unlockMs > now
                          ? t('contest.unlocksIn', { remaining: formatCountdown((unlockMs - now) / 1000) })
                          : t('contest.unlocksSoon')}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDownload(inst.id, inst.name)}
                    disabled={locked}
                    className={`p-2 rounded-lg transition-colors ${
                      locked
                        ? 'text-slate-300 cursor-not-allowed dark:text-gray-600'
                        : 'hover:bg-gray-100 text-violet-500 hover:text-violet-600 dark:hover:bg-slate-700/50 dark:text-violet-400 dark:hover:text-violet-300'
                    }`}
                    title={locked ? t('contest.locked') : t('contest.downloadInput')}
                  >
                    <FileDown className="w-5 h-5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
      )}

      {/* Participants — visible to everyone who can see the contest, even if
          they haven't registered themselves. Collapsed by default. */}
      <div className="glass-card overflow-hidden">
        <button
          onClick={() => setShowParticipants(!showParticipants)}
          className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors dark:hover:bg-slate-800/30"
        >
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-white">
            <Users className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('contest.participants')}
            <span className="text-xs font-normal text-slate-400 ml-1 dark:text-gray-500">
              ({participants.length})
            </span>
          </h2>
          {showParticipants ? (
            <ChevronUp className="w-5 h-5 text-slate-400 dark:text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400 dark:text-gray-400" />
          )}
        </button>
        {showParticipants && (
          <div className="px-5 pb-5">
            {participants.length === 0 ? (
              <p className="text-sm text-slate-400 italic dark:text-gray-600">
                {t('contest.noParticipants')}
              </p>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {participants.map((p) => (
                  <div
                    key={p.id}
                    className={`flex items-center gap-2 py-2 px-3 rounded-lg bg-white border dark:bg-slate-700/20 ${
                      p.disqualified
                        ? 'border-red-500/40 opacity-70'
                        : 'border-gray-200 dark:border-transparent'
                    }`}
                    title={p.disqualified ? p.disqualified_reason || t('contest.disqualified') : undefined}
                  >
                    {p.kind === 'team' ? (
                      <>
                        <Users className="w-4 h-4 text-violet-500 flex-shrink-0 dark:text-violet-400" />
                        <span className={`text-sm truncate ${p.disqualified ? 'line-through text-slate-400 dark:text-gray-500' : 'text-slate-700 dark:text-gray-200'}`}>
                          {p.team_name}
                        </span>
                      </>
                    ) : (
                      <>
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500/30 to-indigo-500/30 flex items-center justify-center text-xs font-bold text-violet-700 flex-shrink-0 dark:text-violet-300">
                          {(p.username || '?')[0].toUpperCase()}
                        </div>
                        <span className={`text-sm truncate ${p.disqualified ? 'line-through text-slate-400 dark:text-gray-500' : 'text-slate-700 dark:text-gray-200'}`}>
                          {p.username}
                        </span>
                      </>
                    )}
                    {user?.is_admin && (
                      <button
                        type="button"
                        onClick={async () => {
                          const next = !p.disqualified;
                          let reason = null;
                          if (next) {
                            reason = await prompt({
                              title: t('contest.disqualifyReasonTitle') || t('contest.disqualifyReasonPrompt'),
                              message: t('contest.disqualifyReasonPrompt'),
                              defaultValue: '',
                            });
                            // ``prompt`` returns null on cancel — stop without DQing.
                            if (reason === null) return;
                          }
                          try {
                            await setRegistrationDisqualified(p.id, {
                              disqualified: next,
                              reason: reason || null,
                            });
                            toast.success(next ? t('contest.toastDisqualified') : t('contest.toastRequalified'));
                            const r = await listContestRegistrations(contest.id);
                            setParticipants(r.data || []);
                          } catch (err) {
                            toast.error(err.response?.data?.detail || t('admin.users.toastFailed'));
                          }
                        }}
                        className={`ml-auto p-1 rounded transition-colors ${
                          p.disqualified
                            ? 'text-emerald-500 hover:bg-emerald-500/10'
                            : 'text-slate-400 hover:text-red-500 hover:bg-red-500/10 dark:text-gray-500'
                        }`}
                        title={p.disqualified ? t('contest.requalify') : t('contest.disqualify')}
                        aria-label={p.disqualified ? t('contest.requalify') : t('contest.disqualify')}
                      >
                        {p.disqualified ? <CheckCircle className="w-3.5 h-3.5" /> : <Ban className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Registration panel — shown before/after submit card to give the user
           an explicit Register/Unregister control. Admins never need to register. */}
      {!user?.is_admin && registration && isBanned && (
        <div className="glass-card p-4 border border-red-500/40 bg-red-500/5 dark:bg-red-500/10">
          <div className="flex items-start gap-3">
            <Ban className="w-6 h-6 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-red-700 dark:text-red-300">
                {t('contest.bannedTitle')}
              </h3>
              <p className="text-sm text-red-700/90 dark:text-red-200/90 mt-1">
                {registration.disqualified_reason || t('contest.bannedReasonNone')}
              </p>
              <p className="text-xs text-red-700/70 dark:text-red-200/70 mt-2">
                {t('contest.bannedHelp')}
              </p>
            </div>
          </div>
        </div>
      )}
      {!user?.is_admin && registration && !isBanned && (
        <div className="glass-card p-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-sm">
            {registration.registered ? (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-500" />
                <span className="text-slate-700 dark:text-gray-200 font-medium">
                  {registration.kind === 'team'
                    ? t('contest.registeredAsTeam')
                    : t('contest.registeredAsSolo')}
                </span>
              </>
            ) : registration.can_register ? (
              <>
                <AlertCircle className="w-5 h-5 text-amber-500" />
                <span className="text-slate-700 dark:text-gray-200">
                  {t('contest.registerToSubmit')}
                </span>
              </>
            ) : (
              <>
                <Lock className="w-5 h-5 text-slate-400" />
                <span className="text-slate-500 dark:text-gray-400">
                  {registration.reason || t('contest.cannotRegister')} —{' '}
                  {t('contest.scoreboardOnly')}
                </span>
              </>
            )}
          </div>
          {registration.registered ? (
            <button
              type="button"
              onClick={handleUnregister}
              disabled={registering}
              className="btn-secondary text-sm py-2 px-3 disabled:opacity-50"
            >
              {registering ? t('contest.registering') : t('contest.unregister')}
            </button>
          ) : registration.can_register ? (
            contest.participation_mode === 'both' ? (
              <div className="flex items-center gap-2 flex-wrap">
                {teams.length > 0 && (
                  <>
                    <select
                      className="input-field text-sm py-1.5"
                      value={selectedTeam || ''}
                      onChange={(e) => setSelectedTeam(e.target.value ? parseInt(e.target.value, 10) : '')}
                    >
                      <option value="">{t('contest.pickTeam')}</option>
                      {teams.map((tm) => (
                        <option key={tm.id} value={tm.id}>{tm.name}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => handleRegister('team')}
                      disabled={registering || !selectedTeam}
                      className="btn-primary text-sm py-2 px-3 disabled:opacity-50"
                      title={t('contest.registerAsTeamTitle')}
                    >
                      {registering ? t('contest.registering') : t('contest.registerAsTeam')}
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => handleRegister('solo')}
                  disabled={registering}
                  className="btn-secondary text-sm py-2 px-3 disabled:opacity-50"
                  title={t('contest.registerSoloTitle')}
                >
                  {t('contest.registerSolo')}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => handleRegister()}
                disabled={registering}
                className="btn-primary text-sm py-2 px-3 disabled:opacity-50"
              >
                {registering ? t('contest.registering') : t('contest.register')}
              </button>
            )
          ) : null}
        </div>
      )}

      {contest.kind !== 'icpc'
        && contest.is_open_for_submissions
        && canParticipate
        && (
          (contest.participation_mode === 'team' && teams.length > 0)
          || contest.participation_mode === 'solo'
          || contest.participation_mode === 'both'
        ) && (
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2 dark:text-white">
            <Upload className="w-5 h-5 text-violet-500 dark:text-violet-400" />
            {t('contest.submitSolution')}
          </h2>
          <form
            onSubmit={handleSubmit}
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !uploading) {
                e.preventDefault();
                e.currentTarget.requestSubmit();
              }
            }}
            className="space-y-4"
          >
            {contest.participation_mode === 'both' && (
              <div className="inline-flex rounded-lg border border-gray-200 p-0.5 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => setSubmitKind('team')}
                  disabled={teams.length === 0}
                  className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                    submitKind === 'team'
                      ? 'bg-violet-600 text-white'
                      : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed'
                  }`}
                >
                  {t('contest.submitAsTeam')}
                </button>
                <button
                  type="button"
                  onClick={() => setSubmitKind('solo')}
                  className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                    submitKind === 'solo'
                      ? 'bg-violet-600 text-white'
                      : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
                  }`}
                >
                  {t('contest.submitAsSolo')}
                </button>
              </div>
            )}
            <div className={submitKind === 'team' && teams.length > 1 ? 'grid sm:grid-cols-2 gap-4' : ''}>
              {submitKind === 'team' && teams.length > 1 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                    {t('contest.teamLabel')}
                  </label>
                  <select
                    className="input-field"
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                  >
                    {teams.map((team) => (
                      <option key={team.id} value={team.id}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 dark:text-gray-300">
                  {t('contest.instanceLabel')}
                </label>
                <select
                  className="input-field"
                  value={selectedInstance}
                  onChange={(e) => setSelectedInstance(e.target.value)}
                >
                  <option value="">{t('contest.chooseInstance')}</option>
                  {contest.instances
                    .filter((inst) => inst.is_unlocked)
                    .map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.name}
                      </option>
                    ))}
                </select>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2 gap-2">
                <label className="block text-sm font-medium text-slate-700 dark:text-gray-300">
                  {t('contest.fileLabel')}
                </label>
                <div className="inline-flex rounded-lg border border-gray-200 p-0.5 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => setSubmitMode('file')}
                    className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                      submitMode === 'file'
                        ? 'bg-violet-600 text-white'
                        : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
                  >
                    <FileTextIcon className="w-3.5 h-3.5" />
                    {t('contest.modeFile')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSubmitMode('code')}
                    className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                      submitMode === 'code'
                        ? 'bg-violet-600 text-white'
                        : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    {t('contest.modeCode')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSubmitMode('source')}
                    className={`text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                      submitMode === 'source'
                        ? 'bg-violet-600 text-white'
                        : 'text-slate-500 hover:text-slate-900 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
                    title={t('contest.modeSourceHint')}
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    {t('contest.modeSource')}
                  </button>
                </div>
              </div>

              {submitMode === 'source' && (
                <div className="mb-2 flex items-center gap-2">
                  <label className="text-xs text-slate-500 dark:text-gray-400">
                    {t('contest.sourceLanguage')}
                  </label>
                  <select
                    className="input-field text-xs py-1 px-2"
                    value={sourceLanguage}
                    onChange={(e) => setSourceLanguage(e.target.value)}
                  >
                    {sourceLanguages.map((l) => (
                      <option key={l.id} value={l.id}>{l.display_name}</option>
                    ))}
                  </select>
                  <span className="text-[11px] text-slate-400 dark:text-gray-500">
                    {t('contest.modeSourceHint')}
                  </span>
                </div>
              )}

              {submitMode === 'file' ? (
                <>
                  <div className="relative">
                    <input
                      type="file"
                      onChange={(e) => setFile(e.target.files[0])}
                      className="input-field file:mr-4 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-violet-600 file:text-white hover:file:bg-violet-500 file:cursor-pointer"
                    />
                  </div>
                  {file && (
                    <p className="text-sm text-slate-500 mt-1.5 dark:text-gray-400">
                      {t('contest.selectedFile', { name: file.name })}
                    </p>
                  )}
                </>
              ) : (
                <div className="rounded-xl border border-gray-300 overflow-hidden dark:border-slate-700">
                  <CodeMirror
                    value={codeText}
                    onChange={(v) => setCodeText(v)}
                    extensions={[python()]}
                    basicSetup={{ lineNumbers: true, highlightActiveLine: false }}
                    theme={theme === 'dark' ? oneDark : 'light'}
                    height="260px"
                  />
                  {submitMode === 'source' && (
                    <p className="text-[11px] text-slate-400 px-2 py-1 bg-gray-50 dark:bg-slate-800/40 dark:text-gray-500">
                      {t('contest.sourceStdinHint')}
                    </p>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <button type="submit" className="btn-primary" disabled={uploading}>
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {t('contest.submitting')}
                  </span>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2 inline" />
                    {t('common.submit')}
                  </>
                )}
              </button>
              <span className="text-[11px] text-slate-400 dark:text-gray-500">
                {t('contest.submitShortcutHint')}
              </span>
              {contest.max_submissions_per_instance && selectedInstance && (
                <span className="text-[11px] text-slate-400 dark:text-gray-500 ml-auto">
                  {t('contest.quotaUsed', {
                    used: submissions.filter((x) => String(x.instance_id) === String(selectedInstance)).length,
                    limit: contest.max_submissions_per_instance,
                  })}
                </span>
              )}
            </div>
          </form>
        </div>
      )}

      {contest.is_open_for_submissions
        && contest.participation_mode === 'team'
        && teams.length === 0
        && !user?.is_admin && (
        <div className="glass-card p-8 text-center">
          <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3 dark:text-amber-400" />
          <p className="text-slate-700 font-medium dark:text-gray-300">{t('contest.joinTeamToSubmit')}</p>
          <Link to="/teams" className="btn-primary text-sm mt-4 inline-block">
            {t('contest.goToTeams')} <ArrowRight className="w-4 h-4 ml-1 inline" />
          </Link>
        </div>
      )}

      {!contest.is_open_for_submissions && contest.start_time && backendIsoMs(contest.start_time) > now && (
        <div className="glass-card p-6 text-center bg-sky-500/5 border border-sky-500/20">
          <Clock className="w-8 h-8 text-sky-600 mx-auto mb-3 dark:text-sky-400" />
          <p className="text-slate-700 font-medium dark:text-gray-200">
            {t('contest.startsIn')}{' '}
            <span className="font-mono tabular-nums text-sky-700 dark:text-sky-300">
              {formatCountdown((backendIsoMs(contest.start_time) - now) / 1000)}
            </span>
          </p>
        </div>
      )}

      {contest.kind !== 'icpc' && submissionsTotal > 0 && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {t('contest.recentSubmissions')}
              <span className="ml-2 text-sm font-normal text-slate-500 dark:text-gray-500">
                ({submissionsTotal})
              </span>
            </h2>
            {submissionsTotal > SUBMISSION_PAGE_SIZE && (
              <div className="flex items-center gap-2 text-sm">
                <button
                  className="btn-secondary text-xs py-1 px-2"
                  disabled={submissionPage === 0}
                  onClick={() => setSubmissionPage((p) => Math.max(0, p - 1))}
                >
                  {t('common.previous')}
                </button>
                <span className="text-slate-500 dark:text-gray-500">
                  {submissionPage * SUBMISSION_PAGE_SIZE + 1}
                  –
                  {Math.min(submissionsTotal, (submissionPage + 1) * SUBMISSION_PAGE_SIZE)}
                  {' '}/ {submissionsTotal}
                </span>
                <button
                  className="btn-secondary text-xs py-1 px-2"
                  disabled={(submissionPage + 1) * SUBMISSION_PAGE_SIZE >= submissionsTotal}
                  onClick={() => setSubmissionPage((p) => p + 1)}
                >
                  {t('common.next')}
                </button>
              </div>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700/50">
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableInstance')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableFile')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableScore')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableStatus')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableBy')}</th>
                  <th className="text-left text-slate-500 font-medium pb-3 pr-4 dark:text-gray-400">{t('contest.tableTime')}</th>
                  <th className="text-right text-slate-500 font-medium pb-3 dark:text-gray-400">{t('mySubmissions.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((s) => (
                  <Fragment key={s.id}>
                  <tr className="border-b border-gray-100 hover:bg-gray-50 dark:border-slate-800/30 dark:hover:bg-slate-800/20">
                    <td className="py-3 pr-4 text-slate-800 max-w-[200px] truncate dark:text-gray-200" title={s.instance_name}>
                      {s.instance_name}
                    </td>
                    <td className="py-3 pr-4 text-slate-500 font-mono text-xs max-w-[200px] truncate dark:text-gray-400" title={s.file_name}>
                      {s.file_name}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className="font-mono font-bold text-violet-600 tabular-nums dark:text-violet-300"
                        title={formatScoreFull(s.score)}
                      >
                        {formatScore(s.score)}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      {s.status === 'scored' ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle className="w-3.5 h-3.5" /> {t('contest.statusScored')}
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setExpandedErrorId(expandedErrorId === s.id ? null : s.id)}
                          className={`inline-flex items-center gap-1 text-red-600 rounded px-1 -mx-1 hover:bg-red-500/10 dark:text-red-400 ${
                            expandedErrorId === s.id ? 'bg-red-500/10 ring-1 ring-red-500/30' : ''
                          }`}
                          title={t('contest.clickForErrorDetail')}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          {s.status === 'invalid_output' ? t('contest.statusInvalidOutput') : t('contest.statusError')}
                          <ChevronDown className={`w-3 h-3 transition-transform ${expandedErrorId === s.id ? 'rotate-180' : ''}`} />
                        </button>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-slate-500 dark:text-gray-400">{s.submitted_by_username}</td>
                    <td className="py-3 pr-4 text-slate-400 text-xs dark:text-gray-500">
                      {new Date(s.submitted_at).toLocaleString()}
                    </td>
                    <td className="py-3 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              const res = await downloadMySubmission(s.id);
                              const url = window.URL.createObjectURL(new Blob([res.data]));
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = s.file_name || `submission_${s.id}.txt`;
                              document.body.appendChild(a);
                              a.click();
                              a.remove();
                              window.URL.revokeObjectURL(url);
                            } catch {
                              toast.error(t('mySubmissions.downloadFailed'));
                            }
                          }}
                          className="p-1.5 rounded hover:bg-gray-100 text-violet-600 hover:text-violet-700 dark:text-violet-400 dark:hover:text-violet-300 dark:hover:bg-slate-800 transition-colors"
                          title={t('mySubmissions.download')}
                          aria-label={t('mySubmissions.download')}
                        >
                          <FileDown className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedErrorId === s.id && s.status !== 'scored' && (
                    <tr className="border-b border-gray-100 bg-red-500/5 dark:border-slate-800/30 dark:bg-red-500/10">
                      <td colSpan={7} className="px-4 py-3">
                        <p className="text-[10px] uppercase text-red-600 mb-1 dark:text-red-400">
                          {s.status === 'invalid_output'
                            ? t('contest.invalidOutputTitle')
                            : t('contest.scoringErrorTitle')}
                        </p>
                        <pre className="text-xs font-mono text-red-700 whitespace-pre-wrap break-all max-h-60 overflow-y-auto dark:text-red-300">
                          {s.error_message || t('contest.genericScoringError')}
                        </pre>
                      </td>
                    </tr>
                  )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
