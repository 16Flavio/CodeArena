import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  getContest, getMyTeams, listIcpcLanguages, getSubmissions,
  getMyContestRegistration, registerToContest, unregisterFromContest,
  listContestRegistrations,
} from '../api';
import { useAuth } from '../AuthContext';
import { AlertCircle, Clock, ArrowRight } from 'lucide-react';
import { useConfirm } from '../components/Confirm';
import HintsPanel from '../components/HintsPanel';
import IcpcContestView from '../components/IcpcContestView';
import ContestHeader from '../components/contest/ContestHeader';
import AnnouncementsPanel from '../components/contest/AnnouncementsPanel';
import ProblemStatementCard from '../components/contest/ProblemStatementCard';
import InstancesCard from '../components/contest/InstancesCard';
import ParticipantsPanel from '../components/contest/ParticipantsPanel';
import RegistrationPanel from '../components/contest/RegistrationPanel';
import SubmitSolutionForm from '../components/contest/SubmitSolutionForm';
import SubmissionsTable from '../components/contest/SubmissionsTable';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { formatCountdown, backendIsoMs } from '../utils/datetime';
import { extractErrorMessage } from '../utils/apiError';

const SUBMISSION_PAGE_SIZE = 25;

export default function ContestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const confirm = useConfirm();
  const { t } = useTranslation();
  const [contest, setContest] = useState(null);
  const [teams, setTeams] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [submissionsTotal, setSubmissionsTotal] = useState(0);
  const [submissionPage, setSubmissionPage] = useState(0);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [submitKind, setSubmitKind] = useState('team'); // 'team' | 'solo' — only relevant when mode is 'both'
  const [sourceLanguages, setSourceLanguages] = useState([]);
  useEffect(() => {
    // Languages come from the ICPC-side endpoint (it's the canonical
    // list of what the judging pipeline supports).
    listIcpcLanguages().then((r) => setSourceLanguages(r.data || [])).catch(() => {});
  }, []);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(Date.now());
  const [registration, setRegistration] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [participants, setParticipants] = useState([]);

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
      toast.error(extractErrorMessage(err, t('contest.toastRegisterFailed')));
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
      toast.error(extractErrorMessage(err, t('contest.toastUnregisterFailed')));
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

  // Called by the submit form after a submission settles — jump back to
  // the first page and re-fetch the list (mirrors the pre-refactor tail
  // of handleSubmit; errors propagate into the form's catch).
  const handleSubmitted = async () => {
    setSubmissionPage(0);
    const r = await getSubmissions(contest.id, selectedTeam || null, SUBMISSION_PAGE_SIZE, 0);
    setSubmissions(r.data.items || []);
    setSubmissionsTotal(r.data.total || 0);
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
      <ContestHeader contest={contest} now={now} />

      <AnnouncementsPanel contestId={contest.id} isAdmin={user?.is_admin} />

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

      <ProblemStatementCard
        contest={contest}
        visible={contest.kind !== 'icpc' && canParticipate}
      />

      {canParticipate && contest.kind !== 'icpc' && (
        <InstancesCard contest={contest} now={now} />
      )}

      <ParticipantsPanel
        contestId={contest.id}
        participants={participants}
        setParticipants={setParticipants}
        isAdmin={user?.is_admin}
      />

      {!user?.is_admin && registration && (
        <RegistrationPanel
          registration={registration}
          isBanned={isBanned}
          registering={registering}
          teams={teams}
          selectedTeam={selectedTeam}
          setSelectedTeam={setSelectedTeam}
          participationMode={contest.participation_mode}
          onRegister={handleRegister}
          onUnregister={handleUnregister}
        />
      )}

      {contest.kind !== 'icpc'
        && contest.is_open_for_submissions
        && canParticipate
        && (
          (contest.participation_mode === 'team' && teams.length > 0)
          || contest.participation_mode === 'solo'
          || contest.participation_mode === 'both'
        ) && (
        <SubmitSolutionForm
          contest={contest}
          teams={teams}
          submitKind={submitKind}
          setSubmitKind={setSubmitKind}
          selectedTeam={selectedTeam}
          setSelectedTeam={setSelectedTeam}
          submissions={submissions}
          sourceLanguages={sourceLanguages}
          onSubmitted={handleSubmitted}
        />
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
        <SubmissionsTable
          submissions={submissions}
          submissionsTotal={submissionsTotal}
          submissionPage={submissionPage}
          setSubmissionPage={setSubmissionPage}
          pageSize={SUBMISSION_PAGE_SIZE}
        />
      )}
    </div>
  );
}
