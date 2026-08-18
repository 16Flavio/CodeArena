import axios from 'axios';
import toast from 'react-hot-toast';
import i18n from './i18n';
import { getToken, clearToken } from './utils/tokenStore';

const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Throttle the 429 toast - a burst of rate-limited requests shouldn't stack
// identical toasts on screen.
let last429ToastAt = 0;

// FastAPI's 422 returns ``detail`` as an *array* of validation objects
// (``[{loc, msg, type}, ...]``). Most call sites pipe
// ``err.response.data.detail`` straight into ``toast.error()``, which
// passes it as React children - and React throws "Objects are not
// valid as a React child" on raw objects, blanking the whole page
// when no error boundary catches it (real bug report: AccountModal's
// wrong-field-name change-username crash). Collapse the array to a
// readable string once, so every call site stays safe.
//
// Object-shape ``detail`` (e.g. the TOTP_REQUIRED challenge: ``{code:
// "TOTP_REQUIRED", params: {challenge_token: "..."}}``) is *intentional
// structured data* - the login UI reads ``detail.code`` to pivot to
// the TOTP form. We must leave it alone. Likewise plain strings.
function _normaliseErrorDetail(err) {
  const detail = err?.response?.data?.detail;
  if (!Array.isArray(detail)) return;
  err.response.data.detail = detail
    .map((e) => (e && typeof e === 'object' && typeof e.msg === 'string')
      ? e.msg
      : String(e))
    .join('; ');
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    _normaliseErrorDetail(err);
    if (err.response?.status === 401) {
      clearToken();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    if (err.response?.status === 429) {
      const now = Date.now();
      if (now - last429ToastAt > 3000) {
        last429ToastAt = now;
        const retry = Number(err.response.headers?.['retry-after']);
        const msg = Number.isFinite(retry) && retry > 0
          ? i18n.t('rateLimit.tooManyRequestsWithSeconds', { seconds: retry })
          : i18n.t('rateLimit.tooManyRequests');
        toast.error(msg, { id: 'rate-limit' });
      }
    }
    return Promise.reject(err);
  },
);

// Auth
export const registerUser = (data) => api.post('/auth/register', data);
export const loginUser = (data) => api.post('/auth/login', data);
export const totpLoginVerify = (data) => api.post('/auth/2fa/login-verify', data);
export const totpSetup = () => api.post('/auth/2fa/setup');
export const totpVerify = (data) => api.post('/auth/2fa/verify', data);
export const totpDisable = (data) => api.post('/auth/2fa/disable', data);
export const getMe = () => api.get('/auth/me');
export const forgotPassword = (data) => api.post('/auth/forgot-password', data);
export const resetPassword = (data) => api.post('/auth/reset-password', data);
export const changePassword = (data) => api.post('/auth/change-password', data);
export const changeUsername = (data) => api.post('/auth/change-username', data);
export const verifyEmail = (token) => api.post('/auth/verify-email', { token });
export const resendVerification = () => api.post('/auth/resend-verification');

// Teams
export const getMyTeams = () => api.get('/teams/my');
export const createTeam = (data) => api.post('/teams', data);
export const joinTeam = (data) => api.post('/teams/join', data);
export const getTeam = (id) => api.get(`/teams/${id}`);
export const leaveTeam = (id) => api.delete(`/teams/${id}/leave`);
export const deleteTeam = (id) => api.delete(`/teams/${id}`);
export const regenerateJoinCode = (id) => api.post(`/teams/${id}/regenerate-code`);
export const removeMember = (teamId, userId) => api.delete(`/teams/${teamId}/members/${userId}`);
export const setMemberPermissions = (teamId, userId, data) =>
  api.put(`/teams/${teamId}/members/${userId}/permissions`, data);
export const transferOwnership = (teamId, newOwnerUserId) =>
  api.post(`/teams/${teamId}/transfer-ownership`, { new_owner_user_id: newOwnerUserId });

// Team discovery + join requests
export const browseTeams = () => api.get('/teams/browse');
export const requestJoin = (teamId, message) =>
  api.post(`/teams/${teamId}/request`, { message });
export const getIncomingRequests = () => api.get('/teams/requests/incoming');
export const getIncomingRequestsCount = () => api.get('/teams/requests/incoming/count');
export const getOutgoingRequests = () => api.get('/teams/requests/outgoing');
export const acceptRequest = (id) => api.post(`/teams/requests/${id}/accept`);
export const rejectRequest = (id) => api.post(`/teams/requests/${id}/reject`);
export const cancelRequest = (id) => api.delete(`/teams/requests/${id}`);

// Contests
export const getContests = () => api.get('/contests');
export const getContest = (id) => api.get(`/contests/${id}`);
export const createContest = (data) => api.post('/contests', data);
export const updateContest = (id, data) => api.put(`/contests/${id}`, data);
export const deleteContest = (id) => api.delete(`/contests/${id}`);
export const uploadProblemStatement = (contestId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/contests/${contestId}/problem-statement`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const deleteProblemStatement = (contestId) =>
  api.delete(`/contests/${contestId}/problem-statement`);
export const downloadProblemStatement = (contestId) =>
  api.get(`/contests/${contestId}/problem-statement`, { responseType: 'blob' });

// Contest participants (polymorphic allowlist for private contests)
export const listContestParticipants = (contestId) =>
  api.get(`/contests/${contestId}/participants`);
export const addContestParticipantUser = (contestId, userId) =>
  api.post(`/contests/${contestId}/participants`, { user_id: userId });
export const addContestParticipantTeam = (contestId, teamId) =>
  api.post(`/contests/${contestId}/participants`, { team_id: teamId });
export const removeContestParticipant = (contestId, entryId) =>
  api.delete(`/contests/${contestId}/participants/${entryId}`);

// Contest co-organizers (per-contest management delegation)
export const listContestOrganizers = (contestId) =>
  api.get(`/contests/${contestId}/organizers`);
export const addContestOrganizer = (contestId, userId) =>
  api.post(`/contests/${contestId}/organizers`, { user_id: userId });
export const removeContestOrganizer = (contestId, userId) =>
  api.delete(`/contests/${contestId}/organizers/${userId}`);

// Contest self-registration
export const getMyContestRegistration = (contestId) =>
  api.get(`/contests/${contestId}/my-registration`);
export const registerToContest = (contestId, payload = {}) =>
  api.post(`/contests/${contestId}/register`, payload);
export const unregisterFromContest = (contestId) =>
  api.delete(`/contests/${contestId}/register`);
export const listContestRegistrations = (contestId) =>
  api.get(`/contests/${contestId}/registrations`);
// Ids of the contests the caller is registered in (solo or via a team).
export const getMyRegisteredContestIds = () =>
  api.get('/contests/registrations/mine');

// Instances
export const getInstances = (contestId) => api.get(`/contests/${contestId}/instances`);
export const createInstance = (contestId, formData) =>
  api.post(`/contests/${contestId}/instances`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const deleteInstance = (id) => api.delete(`/contests/instances/${id}`);
export const updateInstance = (id, formData) =>
  api.patch(`/contests/instances/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const downloadInstance = (id) =>
  api.get(`/contests/instances/${id}/download`, { responseType: 'blob' });

// Submissions
export const submitSolution = (contestId, instanceId, formData) =>
  api.post(`/contests/${contestId}/instances/${instanceId}/submit`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
// Code-based submit: server compiles + runs the source, captures stdout,
// then feeds that to the validator + scorer.
export const submitSolutionCode = (contestId, instanceId, formData) =>
  api.post(`/contests/${contestId}/instances/${instanceId}/submit-code`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const getSubmissions = (contestId, teamId, limit = 50, offset = 0) =>
  api.get(`/contests/${contestId}/submissions`, {
    params: { team_id: teamId, limit, offset },
  });
export const getSubmission = (submissionId) =>
  api.get(`/contests/submissions/${submissionId}`);
export const getMySubmissions = (limit = 50, params = {}) =>
  api.get('/contests/my-submissions', { params: { limit, ...params } });
// Most recent own submission on one ICPC problem. Used to restore the
// judging panel after a page reload.
export const getMyLatestProblemSubmission = (contestId, problemId) =>
  api.get('/contests/my-submissions', {
    params: { limit: 1, contest_id: contestId, problem_id: problemId },
  });
export const downloadMySubmission = (submissionId) =>
  api.get(`/contests/submissions/${submissionId}/file`, { responseType: 'blob' });
export const getSubmissionContent = (submissionId) =>
  api.get(`/contests/submissions/${submissionId}/content`);
export const getMyActivity = (limit = 30) =>
  api.get('/contests/activity/mine', { params: { limit } });
export const markActivitySeen = () => api.post('/contests/activity/seen');

// Hints
export const listHints = (contestId) => api.get(`/contests/${contestId}/hints`);
export const createHint = (contestId, data) => api.post(`/contests/${contestId}/hints`, data);
export const updateHint = (hintId, data) => api.patch(`/contests/hints/${hintId}`, data);
export const deleteHint = (hintId) => api.delete(`/contests/hints/${hintId}`);
export const unlockHint = (hintId) => api.post(`/contests/hints/${hintId}/unlock`);

// Scoring queue
export const getScoringStats = () => api.get('/admin/scoring-stats');

// Admin digest
export const triggerAdminDigest = () => api.post('/admin/send-digest');

// Admin rejudge - works for both output-scoring and ICPC submissions.
export const rejudgeSubmission = (submissionId) =>
  api.post(`/admin/submissions/${submissionId}/rejudge`);

// Admin: toggle disqualification on a registration
export const setRegistrationDisqualified = (registrationId, data) =>
  api.patch(`/contests/registrations/${registrationId}/disqualify`, data);

// ── ICPC mode ────────────────────────────────────────────────────────────────
export const listIcpcLanguages = () => api.get('/icpc/languages');
export const listIcpcProblems = (contestId) => api.get(`/contests/${contestId}/problems`);
export const createIcpcProblem = (contestId, data) =>
  api.post(`/contests/${contestId}/problems`, data);
export const deleteIcpcProblem = (problemId) =>
  api.delete(`/icpc/problems/${problemId}`);
export const updateIcpcProblem = (problemId, data) =>
  api.patch(`/icpc/problems/${problemId}`, data);
export const uploadIcpcProblemStatement = (problemId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/icpc/problems/${problemId}/statement`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const deleteIcpcProblemStatement = (problemId) =>
  api.delete(`/icpc/problems/${problemId}/statement`);
export const addIcpcTestcase = (problemId, data) =>
  api.post(`/icpc/problems/${problemId}/testcases`, data);
export const listIcpcTestcases = (problemId) =>
  api.get(`/icpc/problems/${problemId}/testcases`);
export const updateIcpcTestcase = (testcaseId, data) =>
  api.patch(`/icpc/testcases/${testcaseId}`, data);
export const deleteIcpcTestcase = (testcaseId) =>
  api.delete(`/icpc/testcases/${testcaseId}`);
// Judge a reference solution against a problem's testcases WITHOUT
// persisting a Submission/Judging row - admin sanity check before a
// contest opens. Synchronous on the server (compile + all runs), so
// give it a generous timeout.
export const dryRunIcpcProblem = (problemId, data) =>
  api.post(`/icpc/problems/${problemId}/dry-run`, data, { timeout: 180000 });
// Re-queue every submission of an ICPC contest (optionally one problem)
// through the judging pipeline.
export const rejudgeAllIcpc = (contestId, problemId = null) =>
  api.post(`/contests/${contestId}/rejudge-all`, {}, {
    params: problemId ? { problem_id: problemId } : {},
    timeout: 300000,
  });
export const submitIcpc = (contestId, problemId, formData) =>
  api.post(`/contests/${contestId}/problems/${problemId}/submit`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const getJudging = (submissionId) =>
  api.get(`/contests/submissions/${submissionId}/judging`);
export const getIcpcScoreboard = (contestId) =>
  api.get(`/contests/${contestId}/icpc-scoreboard`);
export const listClarifications = (contestId) =>
  api.get(`/contests/${contestId}/clarifications`);
export const createClarification = (contestId, data) =>
  api.post(`/contests/${contestId}/clarifications`, data);
export const answerClarification = (clarId, data) =>
  api.post(`/icpc/clarifications/${clarId}/answer`, data);
export const updateClarification = (clarId, data) =>
  api.patch(`/icpc/clarifications/${clarId}`, data);
export const deleteClarification = (clarId) =>
  api.delete(`/icpc/clarifications/${clarId}`);
export const importDomjudgePackage = (contestId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/contests/${contestId}/import-domjudge-package`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const scoreboardCsvUrl = (contestId) => `/api/contests/${contestId}/scoreboard.csv`;
export const icpcScoreboardCsvUrl = (contestId) => `/api/contests/${contestId}/icpc-scoreboard.csv`;
export const getIcpcPresentation = (contestId) =>
  api.get(`/contests/${contestId}/icpc-presentation`);
export const getScoringPresentation = (contestId) =>
  api.get(`/contests/${contestId}/scoring-presentation`);
export const duplicateContest = (id) => api.post(`/contests/${id}/duplicate`);

// Scoreboard
export const getScoreboard = (contestId) => api.get(`/contests/${contestId}/scoreboard`);
export const scoreboardStreamUrl = (contestId) =>
  `/api/contests/${contestId}/scoreboard/stream`;
// Short-lived (60s) ticket for query-string auth on the SSE stream, so the
// long-lived session token never lands in a URL. Sent with the normal Bearer
// header via the axios interceptor.
export const getStreamTicket = () => api.post('/auth/stream-ticket');

// Open a problem-statement PDF in a new tab without ever putting the durable
// session token in a URL. We mint a short-lived stream ticket, fetch the PDF
// as a blob with that ticket (a fetch URL isn't recorded in browser history),
// then point the tab at the blob: URL - so the visible URL carries no token
// at all, and the ticket itself expires in ~60s. Mirrors the CSV download.
export async function openStatementPdf(contestId, problemId, version = 0) {
  // Open the tab synchronously (inside the click gesture) so popup blockers
  // don't kill it after the awaits below.
  const win = window.open('', '_blank');
  try {
    const { data } = await getStreamTicket();
    const url =
      `/api/contests/${contestId}/problems/${problemId}/statement` +
      `?token=${encodeURIComponent(data.ticket)}&v=${version || 0}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    const blob = await r.blob();
    const objectUrl = URL.createObjectURL(blob);
    if (win) win.location = objectUrl;
    else window.open(objectUrl, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
  } catch (e) {
    if (win) win.close();
    throw e;
  }
}

// Download a problem attachment (interactive problems ship a local testing
// tool; some problems ship data files). Same short-lived-ticket dance as the
// statement PDF - the durable session token never enters a URL - then a
// synthetic <a download> click so the browser saves the file under its real
// name instead of rendering it.
export async function downloadProblemAttachment(contestId, problemId, attachmentId, filename) {
  const { data } = await getStreamTicket();
  const url =
    `/api/contests/${contestId}/problems/${problemId}/attachments/${attachmentId}` +
    `?token=${encodeURIComponent(data.ticket)}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  const blob = await r.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename || 'attachment';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
}


// Announcements
export const listAnnouncements = (contestId) =>
  api.get(`/contests/${contestId}/announcements`);
export const createAnnouncement = (contestId, data) =>
  api.post(`/contests/${contestId}/announcements`, data);
export const deleteAnnouncement = (id) =>
  api.delete(`/contests/announcements/${id}`);

// Scoring dry-run
export const testScoring = (contestId, data) =>
  api.post(`/contests/${contestId}/test-scoring`, data);

// Rescore every submission for a contest (admin only).
export const rescoreContest = (contestId) =>
  api.post(`/contests/${contestId}/rescore`, {}, { timeout: 300000 });

// Server clock
export const getServerTime = () => api.get('/time');

// Rankings
export const getMyRankings = () => api.get('/teams/my/rankings');

// Leagues - season-long rankings over a set of contests. Students only
// see published leagues; the admin CRUD lives in LeaguesTab.
export const listLeagues = () => api.get('/leagues');
export const getLeague = (id) => api.get(`/leagues/${id}`);
export const createLeague = (data) => api.post('/leagues', data);
export const updateLeague = (id, data) => api.put(`/leagues/${id}`, data);
export const deleteLeague = (id) => api.delete(`/leagues/${id}`);
export const addLeagueEvent = (leagueId, data) =>
  api.post(`/leagues/${leagueId}/events`, data);
export const updateLeagueEvent = (leagueId, eventId, data) =>
  api.put(`/leagues/${leagueId}/events/${eventId}`, data);
export const removeLeagueEvent = (leagueId, eventId) =>
  api.delete(`/leagues/${leagueId}/events/${eventId}`);
export const recomputeLeagueEvent = (leagueId, eventId) =>
  api.post(`/leagues/${leagueId}/events/${eventId}/recompute`);

// Admin
export const getUsers = () => api.get('/admin/users');
export const toggleAdmin = (id) => api.put(`/admin/users/${id}/toggle-admin`);
export const toggleOrganizer = (id) => api.put(`/admin/users/${id}/toggle-organizer`);
export const deleteUser = (id) => api.delete(`/admin/users/${id}`);
// Admin escape hatch: wipe a user's 2FA state when they lost their
// device + recovery codes. The admin verifies identity offline.
export const adminDisableTotp = (id) => api.post(`/admin/users/${id}/totp/disable`);
export const getAuditLog = (params = { limit: 200 }) =>
  api.get('/admin/audit-log', { params });
export const adminListSubmissions = (params = {}) =>
  api.get('/admin/submissions', { params });
export const adminSubmissionsStats = (params = {}) =>
  api.get('/admin/submissions/stats', { params });
export const adminGetSubmissionContent = (id) =>
  api.get(`/admin/submissions/${id}/content`, { responseType: 'text' });
export const adminDeleteSubmission = (id) =>
  api.delete(`/admin/submissions/${id}`);

// Scoring workers - live RQ snapshot + requeue-failed action.
export const getScoringWorkers = () => api.get('/admin/scoring/workers');
export const requeueFailedJobs = () => api.post('/admin/scoring/requeue-failed');

// Python packages
export const getPackages = () => api.get('/admin/packages');
export const getPackageEnvInfo = () => api.get('/admin/packages/info');
export const installPackage = (name) =>
  api.post('/admin/packages/install', { name }, { timeout: 240000 });
export const uninstallPackage = (name) =>
  api.delete(`/admin/packages/${encodeURIComponent(name)}`, { timeout: 240000 });

// Affiliations (schools/organisations)
export const listAffiliations = () => api.get('/icpc/affiliations');
export const createAffiliation = (payload) => api.post('/icpc/affiliations', payload);
export const updateAffiliation = (id, payload) => api.patch(`/icpc/affiliations/${id}`, payload);
export const deleteAffiliation = (id) => api.delete(`/icpc/affiliations/${id}`);
export const setMySoloAffiliation = (affiliation_id) =>
  api.post('/icpc/me/solo-affiliation', { affiliation_id });
export const setTeamAffiliation = (teamId, affiliation_id) =>
  api.post(`/icpc/teams/${teamId}/affiliation`, { affiliation_id });

// Learning zone - student-facing
export const learnListSections = () => api.get('/learning/sections');
export const learnListLessons = (slug) => api.get(`/learning/sections/${encodeURIComponent(slug)}/lessons`);
export const learnGetLesson = (id) => api.get(`/learning/lessons/${id}`);
export const learnSetProgress = (id, status) =>
  api.put(`/learning/lessons/${id}/progress`, { status });

// Learning zone - admin-only
export const adminLearnListSections = () => api.get('/admin/learning/sections');
export const adminLearnCreateSection = (data) => api.post('/admin/learning/sections', data);
export const adminLearnUpdateSection = (id, data) =>
  api.put(`/admin/learning/sections/${id}`, data);
export const adminLearnDeleteSection = (id) => api.delete(`/admin/learning/sections/${id}`);
export const adminLearnListLessons = (sectionId) =>
  api.get(`/admin/learning/sections/${sectionId}/lessons`);
export const adminLearnCreateLesson = (sectionId, data) =>
  api.post(`/admin/learning/sections/${sectionId}/lessons`, data);
export const adminLearnUpdateLesson = (id, data) =>
  api.put(`/admin/learning/lessons/${id}`, data);
export const adminLearnDeleteLesson = (id) => api.delete(`/admin/learning/lessons/${id}`);
export const adminLearnUploadAsset = (lessonId, file, kind = 'image') => {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('kind', kind);
  return api.post(`/admin/learning/lessons/${lessonId}/assets`, fd);
};
export const adminLearnDeleteAsset = (assetId) =>
  api.delete(`/admin/learning/assets/${assetId}`);
export const adminLearnExportLatex = (lang = 'fr') =>
  api.get(`/admin/learning/export/latex?lang=${encodeURIComponent(lang)}`, {
    responseType: 'blob',
    timeout: 60000,
  });

// Lesson exercises - inline coding tasks.
export const learnGetExercise = (id) => api.get(`/learning/exercises/${id}`);
export const learnRunExercise = (id, code, language = '') =>
  api.post(`/learning/exercises/${id}/run`, { code, language }, { timeout: 60000 });
export const adminLearnListExercises = (lessonId) =>
  api.get(`/admin/learning/lessons/${lessonId}/exercises`);
export const adminLearnCreateExercise = (lessonId, data) =>
  api.post(`/admin/learning/lessons/${lessonId}/exercises`, data);
export const adminLearnUpdateExercise = (id, data) =>
  api.put(`/admin/learning/exercises/${id}`, data);
export const adminLearnDeleteExercise = (id) =>
  api.delete(`/admin/learning/exercises/${id}`);

// Custom widgets - student-facing list (used to hydrate the runtime
// registry) + admin CRUD.
export const learnListWidgets = () => api.get('/learning/widgets');
export const adminLearnListWidgets = () => api.get('/admin/learning/widgets');
export const adminLearnCreateWidget = (data) => api.post('/admin/learning/widgets', data);
export const adminLearnGetWidget = (id) => api.get(`/admin/learning/widgets/${id}`);
export const adminLearnUpdateWidget = (id, data) =>
  api.put(`/admin/learning/widgets/${id}`, data);
export const adminLearnDeleteWidget = (id) =>
  api.delete(`/admin/learning/widgets/${id}`);

// Jury verdict override
export const overrideJudging = (judgingId, payload) =>
  api.post(`/icpc/judgings/${judgingId}/override`, payload);

// Jury score override for output-scoring submissions (reason mandatory,
// lands in the audit log).
export const overrideSubmissionScore = (submissionId, data) =>
  api.post(`/contests/submissions/${submissionId}/override-score`, data);

// ICPC contest stats
export const getIcpcStats = (contestId) =>
  api.get(`/contests/${contestId}/icpc-stats`);

// CLICS event feed - admin-only NDJSON snapshot, fetched as raw text.
export const getIcpcEventFeedUrl = (contestId) =>
  `/api/contests/${contestId}/event-feed`;

// Export one ICPC problem as a DOMjudge/Kattis-shaped ZIP.
export const exportIcpcProblem = (problemId) =>
  api.get(`/icpc/problems/${problemId}/export`, { responseType: 'blob' });

export default api;
