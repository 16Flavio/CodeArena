import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# Email addresses are matched case-insensitively everywhere that matters:
# registration checks uniqueness, /forgot-password looks the address up
# lower-cased. Normalise ONCE, at the edge, so those two can never
# disagree. Before this, an address stored with any uppercase letter was
# unreachable by password reset - and since that endpoint always answers
# "if this email is registered, a link has been sent", the failure was
# permanent and completely silent. Case-folding also stops two accounts
# that differ only in case from coexisting.
#
# Deliberately a regex and NOT pydantic's ``EmailStr``: EmailStr requires
# the ``email-validator`` package, which is not in requirements.txt -
# switching to it would raise at import time and take the whole API down.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
_EMAIL_MAX_LENGTH = 254  # RFC 5321 practical ceiling


def _normalise_email(value: str) -> str:
    email = (value or "").strip().lower()
    if len(email) > _EMAIL_MAX_LENGTH:
        raise ValueError("Adresse email trop longue")
    if not _EMAIL_RE.match(email):
        raise ValueError("Adresse email invalide")
    return email


# Closed sets enforced at the schema layer so an invalid string can't
# slip into the DB. Kept as constants (not Literals) so they can be
# referenced from validators without re-importing typing.Literal.
_PARTICIPATION_MODES = {"team", "solo", "both"}
_CONTEST_KINDS = {"output", "icpc"}


def _check_choice(value, valid_set, field_name):
    if value is None:
        return value
    if value not in valid_set:
        raise ValueError(
            f"{field_name}: '{value}' is not one of {sorted(valid_set)}"
        )
    return value
from datetime import datetime
from typing import Optional


def _validate_contest_date_ordering(values):
    """Enforce a sensible ordering between the contest dates.
    Skipped for any field that's None (nullable)."""
    vis = values.get("visible_at")
    start = values.get("start_time")
    freeze = values.get("freeze_scoreboard_at")
    end = values.get("end_time")
    hidden = values.get("hidden_at")

    pairs = [
        ("visible_at", vis, "start_time", start),
        ("start_time", start, "freeze_scoreboard_at", freeze),
        ("start_time", start, "end_time", end),
        ("freeze_scoreboard_at", freeze, "end_time", end),
        ("end_time", end, "hidden_at", hidden),
    ]
    for a_name, a, b_name, b in pairs:
        if a is not None and b is not None and a > b:
            raise ValueError(
                f"{a_name} ({a.isoformat()}) must be on or before "
                f"{b_name} ({b.isoformat()})"
            )
    return values


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalise(cls, v: str) -> str:
        return _normalise_email(v)


class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangeUsernameRequest(BaseModel):
    current_password: str
    new_username: str


class VerifyEmailRequest(BaseModel):
    token: str


class TotpSetupOut(BaseModel):
    """Response from POST /auth/2fa/setup. ``otpauth_url`` is what
    the client encodes as a QR code; ``secret`` is shown alongside in
    case the authenticator app doesn't accept QR scanning."""
    secret: str
    otpauth_url: str


class TotpVerifyIn(BaseModel):
    code: str


class TotpVerifyOut(BaseModel):
    recovery_codes: list[str]


class TotpDisableIn(BaseModel):
    password: str
    code: str


class TotpLoginVerifyIn(BaseModel):
    challenge_token: str
    code: str


class SimpleMessage(BaseModel):
    detail: str


class ChangePasswordOut(BaseModel):
    detail: str
    # Fresh session token: changing the password bumps ``token_version``
    # (revoking every outstanding token), so the caller needs a
    # replacement or they'd be logged out by their own change.
    access_token: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_organizer: bool = False
    email_verified: bool = False
    totp_enabled: bool = False
    solo_affiliation_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str


class TeamJoin(BaseModel):
    join_code: str


class TeamMemberOut(BaseModel):
    id: int
    user_id: int
    username: str
    role: str
    can_submit: bool = True
    joined_at: datetime

    class Config:
        from_attributes = True


class MemberPermissionUpdate(BaseModel):
    can_submit: bool


class TeamOut(BaseModel):
    id: int
    name: str
    join_code: str
    created_at: datetime
    members: list[TeamMemberOut] = []

    class Config:
        from_attributes = True


class TeamBrowseOut(BaseModel):
    id: int
    name: str
    member_count: int
    is_full: bool
    is_member: bool
    has_pending_request: bool
    created_at: datetime


class JoinRequestCreate(BaseModel):
    message: Optional[str] = ""


class JoinRequestOut(BaseModel):
    id: int
    team_id: int
    team_name: str
    user_id: int
    username: str
    message: str
    status: str
    created_at: datetime
    decided_at: Optional[datetime] = None


class JoinRequestCount(BaseModel):
    pending: int


# ── Announcements ────────────────────────────────────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str = ""
    body: str


class AnnouncementOut(BaseModel):
    id: int
    contest_id: int
    title: str
    body: str
    created_at: datetime
    created_by: Optional[int] = None
    author_username: Optional[str] = None


# ── Scoring test ──────────────────────────────────────────────────────────────

class TestScoringRequest(BaseModel):
    instance_id: int
    submission_data: str
    # Scoring-script override. Ignored when mode == "validate".
    script_override: Optional[str] = None
    # "score" (default) runs the scoring script and returns a numeric
    # score. "validate" runs the output validator and surfaces its
    # error message (or ok=True if the output is accepted).
    mode: str = "score"
    validator_override: Optional[str] = None


class TestScoringResult(BaseModel):
    ok: bool
    score: Optional[float] = None
    error: Optional[str] = None
    duration_ms: int


# ── Rankings ──────────────────────────────────────────────────────────────────

class TeamContestRanking(BaseModel):
    # None for solo participation.
    team_id: Optional[int] = None
    team_name: str
    contest_id: int
    contest_title: str
    # "output" or "icpc" - the frontend formats the score accordingly
    # (points vs problems solved).
    kind: str = "output"
    rank: int
    total_teams: int
    total_score: float
    # ICPC only: problems solved / penalty minutes behind the rank.
    solved: Optional[int] = None
    penalty: Optional[int] = None


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    actor_username: str
    action: str
    target_type: str
    target_id: Optional[int] = None
    detail: str


# ── Rescoring ────────────────────────────────────────────────────────────────

class RescoreResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    unchanged: int
    # Submissions the judge never answered for: left EXACTLY as they were,
    # not re-scored and not marked failed. Counted apart from ``failed``
    # because "the script rejected it" and "no worker answered" call for
    # different actions - the second one just needs a re-run.
    skipped: int = 0


# ── Contests ──────────────────────────────────────────────────────────────────

class ContestCreate(BaseModel):
    title: str
    description: str = ""
    problem_statement: str = ""
    visible_at: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hidden_at: Optional[datetime] = None
    freeze_scoreboard_at: Optional[datetime] = None
    is_active: bool = True
    participation_mode: str = "team"  # "team" | "solo" | "both"
    is_public: bool = True
    practice_mode: bool = False
    kind: str = "output"  # "output" | "icpc"
    dedup_block: bool = False
    min_seconds_between_submits: int = 0
    max_submissions_per_instance: Optional[int] = None
    # None = no per-contest cap (the global team-size cap still applies).
    max_team_size: Optional[int] = Field(default=None, ge=1)
    output_validator_script: Optional[str] = None
    scoring_script: str = "score = 0"

    @field_validator("participation_mode")
    @classmethod
    def _check_participation_mode(cls, v):
        return _check_choice(v, _PARTICIPATION_MODES, "participation_mode")

    @field_validator("kind")
    @classmethod
    def _check_kind(cls, v):
        return _check_choice(v, _CONTEST_KINDS, "kind")

    @model_validator(mode="after")
    def _check_dates(self):
        _validate_contest_date_ordering(self.__dict__)
        return self


class ContestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    problem_statement: Optional[str] = None
    visible_at: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hidden_at: Optional[datetime] = None
    freeze_scoreboard_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    participation_mode: Optional[str] = None
    is_public: Optional[bool] = None
    practice_mode: Optional[bool] = None
    kind: Optional[str] = None
    dedup_block: Optional[bool] = None
    min_seconds_between_submits: Optional[int] = None
    max_submissions_per_instance: Optional[int] = None
    max_team_size: Optional[int] = Field(default=None, ge=1)
    output_validator_script: Optional[str] = None
    scoring_script: Optional[str] = None

    @field_validator("participation_mode")
    @classmethod
    def _check_participation_mode(cls, v):
        return _check_choice(v, _PARTICIPATION_MODES, "participation_mode")

    @field_validator("kind")
    @classmethod
    def _check_kind(cls, v):
        return _check_choice(v, _CONTEST_KINDS, "kind")

    @model_validator(mode="after")
    def _check_dates(self):
        # Only enforce when the caller actually sends dates (partial updates
        # can omit some and should still be accepted).
        _validate_contest_date_ordering(self.__dict__)
        return self


class InstanceOut(BaseModel):
    id: int
    contest_id: int
    name: str
    unlock_delay_seconds: int = 0
    unlock_at_absolute: Optional[datetime] = None
    unlock_at: Optional[datetime] = None  # resolved: absolute if set, else start+delay
    close_at_absolute: Optional[datetime] = None
    is_unlocked: bool = True
    is_closed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ContestOut(BaseModel):
    id: int
    title: str
    description: str
    problem_statement: str
    problem_statement_pdf_name: Optional[str] = None
    has_problem_statement_pdf: bool = False
    visible_at: Optional[datetime] = None
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    hidden_at: Optional[datetime] = None
    freeze_scoreboard_at: Optional[datetime] = None
    is_active: bool
    participation_mode: str = "team"
    is_public: bool = True
    practice_mode: bool = False
    kind: str = "output"
    dedup_block: bool = False
    min_seconds_between_submits: int = 0
    max_submissions_per_instance: Optional[int] = None
    max_team_size: Optional[int] = None
    output_validator_script: Optional[str] = None
    # Derived flags for the current caller (admins bypass gates).
    is_open_for_submissions: bool = False
    is_scoreboard_frozen: bool = False
    scoring_script: str
    created_at: datetime
    instances: list[InstanceOut] = []

    class Config:
        from_attributes = True


class ContestListOut(BaseModel):
    id: int
    title: str
    description: str
    visible_at: Optional[datetime] = None
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    hidden_at: Optional[datetime] = None
    freeze_scoreboard_at: Optional[datetime] = None
    is_active: bool
    participation_mode: str = "team"
    is_public: bool = True
    practice_mode: bool = False
    kind: str = "output"
    is_open_for_submissions: bool = False
    created_at: datetime
    instance_count: int = 0

    class Config:
        from_attributes = True


class ContestParticipantOut(BaseModel):
    id: int
    kind: str  # "user" or "team"
    user_id: Optional[int] = None
    team_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    team_name: Optional[str] = None
    added_at: datetime


class ContestParticipantAdd(BaseModel):
    user_id: Optional[int] = None
    team_id: Optional[int] = None


class ContestRegistrationOut(BaseModel):
    id: int
    kind: str  # "user" or "team"
    user_id: Optional[int] = None
    team_id: Optional[int] = None
    username: Optional[str] = None
    team_name: Optional[str] = None
    registered_at: datetime
    disqualified: bool = False
    disqualified_reason: Optional[str] = None


class ContestRegistrationCreate(BaseModel):
    team_id: Optional[int] = None  # send only for team-mode registrations


class MyRegistrationOut(BaseModel):
    registered: bool
    kind: Optional[str] = None  # "user" | "team" | None
    registration_id: Optional[int] = None
    team_id: Optional[int] = None
    can_register: bool = True  # allowlist gate
    reason: Optional[str] = None  # when can_register is False
    # Surfaced so the contest page can render a "banned" banner instead
    # of the usual submit/unregister controls. The user can't clear this
    # by unregistering - only an admin can.
    disqualified: bool = False
    disqualified_reason: Optional[str] = None


# ── Instances ─────────────────────────────────────────────────────────────────

class InstanceCreate(BaseModel):
    name: str
    unlock_delay_seconds: int = 0
    unlock_at_absolute: Optional[datetime] = None


# ── Submissions ───────────────────────────────────────────────────────────────

class SubmissionOut(BaseModel):
    id: int
    team_id: Optional[int] = None
    team_name: str = ""
    contest_id: int
    # instance_id is only set for output-scoring contests. ICPC submissions
    # populate problem_id + source_language instead. Admin serialisers must
    # read both or ICPC rows will Pydantic-fail the whole page.
    instance_id: Optional[int] = None
    instance_name: str = ""
    problem_id: Optional[int] = None
    problem_label: str = ""
    source_language: Optional[str] = None
    # Latest judging verdict for ICPC submissions ("AC"/"WA"/…). Empty for
    # output-scoring - they use ``status`` + ``score`` instead.
    latest_verdict: str = ""
    latest_judging_id: Optional[int] = None
    file_name: str
    score: Optional[float]
    status: str
    error_message: str
    submitted_at: datetime
    submitted_by: int
    submitted_by_username: str = ""
    submitter_ip: Optional[str] = None
    is_final: bool = False

    class Config:
        from_attributes = True


class PaginatedSubmissions(BaseModel):
    items: list[SubmissionOut]
    total: int
    limit: int
    offset: int


class MySubmissionOut(SubmissionOut):
    contest_title: str = ""


class ActivityItem(BaseModel):
    kind: str  # "announcement" | "team_submission" | "my_result" | "league_published"
    title: str
    body: str = ""
    contest_id: Optional[int] = None
    contest_title: str = ""
    at: datetime


class HintOut(BaseModel):
    id: int
    contest_id: int
    label: str
    cost_fraction: float
    order_idx: int
    unlocked: bool = False
    body: str = ""  # empty unless unlocked (or admin)


class HintAdminIn(BaseModel):
    label: str = ""
    body: str = ""
    cost_fraction: float = 0.1
    order_idx: int = 0


class DisqualifyIn(BaseModel):
    disqualified: bool
    reason: Optional[str] = None


class FinalSubmissionIn(BaseModel):
    submission_id: Optional[int] = None  # null = clear the final flag


# ── ICPC ──────────────────────────────────────────────────────────────────────

class LanguageOut(BaseModel):
    id: str
    display_name: str
    extensions: str
    time_factor: float
    enabled: bool = True

    class Config:
        from_attributes = True


class TestcaseOut(BaseModel):
    id: int
    rank: int
    is_sample: bool
    # Only populated when the caller is admin or the testcase is a sample.
    input_data: str = ""
    expected_output: str = ""
    points: int = 1
    group_name: Optional[str] = None


class ProblemAttachmentOut(BaseModel):
    """One downloadable file shipped with the problem (the interactive
    problems' ``testing_tool.py``, sample inputs, headers). Metadata only -
    the bytes come from the download endpoint."""
    id: int
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0


class SampleInteractionOut(BaseModel):
    """A sample interaction transcript for an interactive problem. ``content``
    is the raw DOMjudge ``.interaction`` text: one message per line, ``<``
    prefix = judge to team, ``>`` prefix = team to judge."""
    name: str = ""
    content: str = ""


class ProblemOut(BaseModel):
    id: int
    contest_id: int
    external_id: str
    label: str
    color: str = ""
    name: str
    time_limit_ms: int
    memory_limit_mb: int
    checker_kind: str = "tokens"
    num_passes: int = 1
    has_interactor: bool = False
    interactor_language: str = "py3"
    has_checker_script: bool = False
    checker_language: str = "py3"
    order_idx: int = 0
    has_statement_pdf: bool = False
    # File mtime (int seconds). Used by the frontend as a cache-buster
    # query param so the URL is stable while the PDF is unchanged but
    # flips on an admin replace - defeats stale browser cache entries
    # that accumulated before we deployed ``Cache-Control: no-store`` on
    # the download endpoint.
    statement_pdf_version: int | None = None
    sample_testcases: list[TestcaseOut] = []
    # Interactive problems have no sample .in/.ans pair - their sample is a
    # transcript instead. Empty for every other problem kind.
    sample_interactions: list[SampleInteractionOut] = []
    attachments: list[ProblemAttachmentOut] = []
    scoring_mode: str = "icpc"


class ProblemAdminIn(BaseModel):
    external_id: str
    label: str
    name: str
    color: str = ""
    time_limit_ms: int = 1000
    memory_limit_mb: int = 2048
    checker_kind: str = "tokens"
    checker_epsilon: Optional[float] = None
    num_passes: int = 1
    interactor_script: Optional[str] = None
    interactor_language: str = "py3"
    order_idx: int = 0
    scoring_mode: str = "icpc"


class TestcaseAdminIn(BaseModel):
    rank: int = 0
    is_sample: bool = False
    input_data: str = ""
    expected_output: str = ""
    points: int = 1
    group_name: Optional[str] = None


class JudgingRunOut(BaseModel):
    testcase_id: int
    verdict: str
    # Wall clock (carries interpreter + container startup).
    runtime_ms: Optional[int] = None
    # CPU time of the contestant process - the figure the time limit is
    # actually checked against. None when unmeasurable (killed run, dev box
    # without POSIX rusage, judging predating the measurement).
    cpu_ms: Optional[int] = None
    is_sample: bool = False
    # First ~1 KB of the program's stdout + stderr on this testcase. Only
    # populated for the submitter / teammates / admin (same authz as the
    # surrounding judging response).
    stdout_truncated: Optional[str] = None
    stderr_truncated: Optional[str] = None


class TestcaseOutline(BaseModel):
    """Identity-only view of a Testcase - id, ordering, and whether it's a
    sample. No input/expected so the secret testcases stay secret. Lets
    the UI render an "unknown" grey chip for testcases that didn't run
    when the judge short-circuited on first failure."""
    id: int
    rank: int
    is_sample: bool


class JudgingOut(BaseModel):
    id: int
    submission_id: int
    verdict: str
    max_runtime_ms: Optional[int] = None
    max_cpu_ms: Optional[int] = None
    # Soft limit actually applied to this submission: the problem's
    # time_limit_ms times the language's time_factor. Saves the UI from
    # re-deriving it (and from showing "1.0 s" next to an accepted 1500 ms).
    time_limit_effective_ms: Optional[int] = None
    language_time_factor: Optional[float] = None
    compile_output: Optional[str] = None
    judged_at: Optional[datetime] = None
    runs: list[JudgingRunOut] = []
    # Full testcase grid for the problem (rank order). The UI matches
    # each entry against ``runs`` by ``testcase_id``; entries with no
    # matching run are rendered as un-evaluated.
    all_testcases: list[TestcaseOutline] = []


class IcpcSubmissionOut(BaseModel):
    id: int
    team_id: Optional[int] = None
    team_name: str = ""
    contest_id: int
    problem_id: int
    problem_label: str = ""
    source_language: str
    submitted_at: datetime
    submitted_by: int
    submitted_by_username: str = ""
    verdict: str = "pending"
    is_final: bool = False
    total_points: Optional[float] = None
    override_reason: Optional[str] = None


class IcpcScoreCell(BaseModel):
    problem_id: int
    label: str
    solved: bool
    attempts: int = 0
    first_solve_minutes: Optional[int] = None
    # Attempts made *after* the freeze that the public can see but the
    # verdict of which is hidden. 0 outside the freeze window. When
    # non-zero and ``solved`` is False, the UI renders the cell as a
    # pale-blue "pending" tile ("?" style, DOMjudge convention).
    pending_attempts: int = 0
    # Submissions still sitting in the judging queue (no verdict yet).
    # DELIBERATELY distinct from ``pending_attempts`` above, which means
    # "judged, but the verdict is withheld until the freeze lifts". This
    # one means "the judge has not answered yet" and clears on its own
    # within seconds. Never affects solved_count or penalty.
    judging_pending: int = 0


class IcpcScoreRow(BaseModel):
    team_id: Optional[int] = None
    team_name: str
    members: list[str] = []
    kind: str = "team"
    solved_count: int = 0
    total_penalty: int = 0
    cells: dict[str, IcpcScoreCell] = {}
    affiliation_id: Optional[int] = None
    affiliation_name: Optional[str] = None


class IcpcScoreboardOut(BaseModel):
    contest_id: int
    contest_title: str
    problems: list[ProblemOut]
    rows: list[IcpcScoreRow]
    frozen: bool = False


class IcpcLanguageStat(BaseModel):
    language_id: str
    submissions: int
    accepted: int


class IcpcFirstSolver(BaseModel):
    label: str
    team_id: Optional[int] = None
    user_id: Optional[int] = None
    team_name: str
    members: list[str] = []
    minute: int


class IcpcMedalEntry(BaseModel):
    rank: int
    team_id: Optional[int] = None
    user_id: Optional[int] = None
    team_name: str
    members: list[str] = []
    affiliation_name: Optional[str] = None
    solved_count: int
    total_penalty: int
    tier: str  # "gold" | "silver" | "bronze" | "" (no medal)


class IcpcPresentationOut(BaseModel):
    """Bundle for the admin-only post-contest presentation. Combines the
    public/frozen view (what the audience sees right now), the truth
    (used for the reveal sequence), the first-to-solve table, and the
    medal podium at top-12."""
    contest_id: int
    contest_title: str
    end_time: Optional[datetime] = None
    problems: list[ProblemOut]
    frozen_state: IcpcScoreboardOut
    final_state: IcpcScoreboardOut
    first_solvers: list[IcpcFirstSolver] = []
    medals: list[IcpcMedalEntry] = []
    # Submission counts grouped by source language. Sorted by total
    # submissions descending; lets the stats scene render a quick
    # "Python vs C++ vs others" breakdown without a second round-trip.
    language_stats: list[IcpcLanguageStat] = []


class IcpcDryRunIn(BaseModel):
    language: str
    source: str


class IcpcDryRunRun(BaseModel):
    rank: int
    is_sample: bool
    verdict: str
    runtime_ms: Optional[int] = None
    stdout: str = ""
    stderr: str = ""


class IcpcDryRunResult(BaseModel):
    verdict: str
    compile_output: Optional[str] = None
    runs: list[IcpcDryRunRun] = []


class AffiliationOut(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    country_code: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class AffiliationIn(BaseModel):
    name: str
    short_name: Optional[str] = None
    country_code: Optional[str] = None
    logo_url: Optional[str] = None


class JudgingOverrideIn(BaseModel):
    verdict: str        # new verdict (AC / WA / TLE / RE / CE / IE / ...)
    reason: str = ""    # short jury note (audit + surfaces in UI)


class SetAffiliationIn(BaseModel):
    affiliation_id: Optional[int] = None  # null removes the affiliation


class IcpcProblemStat(BaseModel):
    problem_id: int
    label: str
    name: str
    submissions: int
    accepted: int
    # First AC, in minutes from contest start. None if nobody solved it.
    first_solve_minutes: Optional[int] = None


class IcpcVerdictCount(BaseModel):
    verdict: str
    count: int


class IcpcStatsOut(BaseModel):
    total_submissions: int
    total_teams: int
    per_problem: list[IcpcProblemStat] = []
    per_language: list[IcpcLanguageStat] = []
    per_verdict: list[IcpcVerdictCount] = []


class ClarificationOut(BaseModel):
    id: int
    contest_id: int
    problem_id: Optional[int] = None
    problem_label: Optional[str] = None
    from_team_id: Optional[int] = None
    from_team_name: Optional[str] = None
    body: str
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    visibility: str = "private"
    created_at: datetime


class ClarificationIn(BaseModel):
    problem_id: Optional[int] = None
    body: str


class ClarificationAnswer(BaseModel):
    answer: str
    visibility: str = "private"  # "public" or "private"


class ScoringStats(BaseModel):
    pending: int
    scored: int
    errors: int
    avg_scoring_ms: Optional[float] = None
    recent_errors: list[dict] = []


# ── Scoreboard ────────────────────────────────────────────────────────────────

class InstanceScore(BaseModel):
    instance_id: int
    best_score: float
    submission_count: int
    # Submissions made after the freeze cutoff for this scope. Verdicts
    # are hidden; the UI uses the count to paint the cell as "?" (first
    # submission ever) or "score +/- ?" (had a pre-freeze score that
    # might still move).
    pending_changes: int = 0
    # Submissions still in the scoring queue (status="pending"). Distinct
    # from ``pending_changes``: that one is about the freeze withholding a
    # known result, this one is about the result not existing yet. Never
    # contributes to best_score or the total.
    judging_pending: int = 0


class TeamScore(BaseModel):
    team_id: Optional[int] = None  # null for solo entries
    team_name: str  # for solo, this is the username
    members: list[str]
    scores: dict[str, InstanceScore]
    total_score: float
    kind: str = "team"  # "team" or "solo"


class ScoreboardOut(BaseModel):
    contest_id: int
    contest_title: str
    instances: list[InstanceOut]
    teams: list[TeamScore]
    frozen: bool = False
    freeze_at: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ScoringInstanceBest(BaseModel):
    """Per-instance "winner" for the scoring presentation - the team
    holding the highest best_score on the instance in the final state.
    Analogue of IcpcFirstSolver for output-style contests."""
    instance_id: int
    instance_name: str
    team_id: Optional[int] = None
    team_name: str
    members: list[str] = []
    best_score: float


class ScoringMedalEntry(BaseModel):
    rank: int
    team_id: Optional[int] = None
    team_name: str
    members: list[str] = []
    total_score: float
    tier: str  # "gold" | "silver" | "bronze" | ""


class ScoringPresentationOut(BaseModel):
    """Bundle for the admin-only post-contest presentation, output
    (Hashcode-style) variant. Mirrors IcpcPresentationOut: frozen view,
    final view, per-instance bests, top-12 podium grouped into tiers."""
    contest_id: int
    contest_title: str
    end_time: Optional[datetime] = None
    instances: list[InstanceOut]
    frozen_state: ScoreboardOut
    final_state: ScoreboardOut
    instance_bests: list[ScoringInstanceBest] = []
    medals: list[ScoringMedalEntry] = []


# ── Learning zone ─────────────────────────────────────────────────────────────

class LearningSectionIn(BaseModel):
    """Admin payload to create / update a section. ``slug`` must be
    URL-safe; the frontend slugifies the title client-side but the
    backend re-validates."""
    slug: str
    title_fr: str
    title_en: str
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    order_idx: int = 0
    is_published: bool = False

    @field_validator("slug")
    @classmethod
    def _slug_shape(cls, v: str) -> str:
        v = (v or "").strip().lower()
        import re
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?", v):
            raise ValueError("slug doit être [a-z0-9-], 1-80 caractères")
        return v


class LearningSectionOut(BaseModel):
    id: int
    slug: str
    order_idx: int
    is_published: bool
    title_fr: str
    title_en: str
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    lesson_count: int = 0
    completed_count: int = 0  # for the calling user

    class Config:
        from_attributes = True


class LessonIn(BaseModel):
    """Admin payload for create / update."""
    slug: str
    title_fr: str
    title_en: str
    content_fr: str = ""
    content_en: str = ""
    order_idx: int = 0
    is_published: bool = False
    exercise_problem_id: Optional[int] = None

    @field_validator("slug")
    @classmethod
    def _slug_shape(cls, v: str) -> str:
        v = (v or "").strip().lower()
        import re
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?", v):
            raise ValueError("slug doit être [a-z0-9-], 1-80 caractères")
        return v


class LessonSummary(BaseModel):
    """Listing entry - no body, cheap to fetch en masse."""
    id: int
    section_id: int
    slug: str
    order_idx: int
    is_published: bool
    title_fr: str
    title_en: str
    has_exercise: bool
    progress_status: Optional[str] = None  # None | "started" | "completed"

    class Config:
        from_attributes = True


class LessonAssetOut(BaseModel):
    id: int
    lesson_id: int
    kind: str
    url: str
    original_name: str

    class Config:
        from_attributes = True


class LessonOut(BaseModel):
    """Full lesson payload - body included. Returned on GET /lessons/{id}."""
    id: int
    section_id: int
    slug: str
    order_idx: int
    is_published: bool
    title_fr: str
    title_en: str
    content_fr: str
    content_en: str
    exercise_problem_id: Optional[int] = None
    progress_status: Optional[str] = None
    assets: list[LessonAssetOut] = []

    class Config:
        from_attributes = True


class LessonProgressIn(BaseModel):
    status: str  # "started" | "completed"

    @field_validator("status")
    @classmethod
    def _status_shape(cls, v: str) -> str:
        if v not in ("started", "completed"):
            raise ValueError("status doit être 'started' ou 'completed'")
        return v


class LessonExerciseTestCase(BaseModel):
    """One test case in an exercise. ``is_sample`` controls whether the
    student sees the input/expected (sample) or only a pass/fail
    (hidden - typical for "are you cheating?" guards)."""
    input: str = ""
    expected: str = ""
    is_sample: bool = True


class LessonExerciseIn(BaseModel):
    """Admin payload for create / update."""
    title_fr: str = ""
    title_en: str = ""
    prompt_fr: str = ""
    prompt_en: str = ""
    language: str = "py3"
    starter_code: str = ""
    test_cases: list[LessonExerciseTestCase] = []
    time_limit_ms: int = 2000

    @field_validator("time_limit_ms")
    @classmethod
    def _time_limit_shape(cls, v: int) -> int:
        # Cap to keep a misconfigured exercise from soaking the worker.
        if v < 100:
            return 100
        if v > 30_000:
            return 30_000
        return v


class LessonExerciseOut(BaseModel):
    """Returned to admins for editing - full content. Student-facing
    listings come through ``LessonExercisePublicOut`` which redacts
    hidden test cases."""
    id: int
    lesson_id: int
    title_fr: str
    title_en: str
    prompt_fr: str
    prompt_en: str
    language: str
    starter_code: str
    test_cases: list[LessonExerciseTestCase]
    time_limit_ms: int

    class Config:
        from_attributes = True


class LessonExercisePublicOut(BaseModel):
    """Student view: hidden test cases are stripped. Only their existence
    is signalled via ``hidden_count`` so the UI can say "12 hidden tests
    will run after you click Run"."""
    id: int
    lesson_id: int
    title_fr: str
    title_en: str
    prompt_fr: str
    prompt_en: str
    language: str
    starter_code: str
    sample_test_cases: list[LessonExerciseTestCase]
    hidden_count: int
    time_limit_ms: int


class LessonExerciseRunIn(BaseModel):
    code: str
    language: str = ""  # if empty, fall back to the exercise's stored language


class LessonExerciseRunResult(BaseModel):
    """One testcase outcome. ``input`` / ``expected`` are blanked out
    for hidden tests so the student can't reverse-engineer them by
    diffing the response."""
    is_sample: bool
    passed: bool
    input: str = ""
    expected: str = ""
    actual: str = ""
    runtime_ms: int = 0
    error: str = ""


class LessonExerciseRunOut(BaseModel):
    all_passed: bool
    compile_output: str = ""
    results: list[LessonExerciseRunResult]


class LearningWidgetIn(BaseModel):
    """Admin payload for a custom widget.

    ``name`` is the directive name (e.g. ``viz-binary-search``); used
    in lesson markdown as ``:::name{...}`` and matched at render time.
    Must be lowercase, [a-z0-9-], 2-80 chars."""
    name: str
    title_fr: str
    title_en: str
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    html_template: str = ""
    params_schema: Optional[str] = None  # JSON string
    example_params: Optional[str] = None  # JSON string
    is_published: bool = False

    @field_validator("name")
    @classmethod
    def _name_shape(cls, v: str) -> str:
        v = (v or "").strip().lower()
        import re
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,79}", v):
            raise ValueError("name doit être [a-z0-9-] et commencer par une lettre, 2-80 caractères")
        return v


class LearningWidgetOut(BaseModel):
    id: int
    name: str
    title_fr: str
    title_en: str
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    html_template: str
    params_schema: Optional[str] = None
    example_params: Optional[str] = None
    is_published: bool

    class Config:
        from_attributes = True


# ─── Leagues ─────────────────────────────────────────────────────────────────

class LeagueCreate(BaseModel):
    name: str
    season: str = ""
    description: str = ""


class LeagueUpdate(BaseModel):
    name: Optional[str] = None
    season: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None


class LeagueEventIn(BaseModel):
    contest_id: int
    coefficient: float = 1.0


class LeagueEventUpdate(BaseModel):
    coefficient: float


class LeagueEventOut(BaseModel):
    id: int
    contest_id: int
    contest_title: str
    contest_kind: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    coefficient: float
    # finished: end_time has passed. counted: results are published into
    # the standings (finished AND scoreboard freeze lifted) - a finished
    # but frozen event shows as "pending reveal" in the UI.
    finished: bool
    counted: bool
    participants: int


class LeagueEventScoreOut(BaseModel):
    event_id: int
    contest_id: int
    contest_title: str
    rank: Optional[int] = None       # None = did not take part
    points: float


class LeagueStandingRowOut(BaseModel):
    rank: int
    user_id: int
    username: str
    total_points: float
    events_played: int
    wins: int
    per_event: list[LeagueEventScoreOut]


class LeagueOut(BaseModel):
    id: int
    name: str
    season: str
    description: str
    is_published: bool
    created_at: Optional[datetime] = None
    events: list[LeagueEventOut] = []

    class Config:
        from_attributes = True


class LeagueStandingsOut(BaseModel):
    league: LeagueOut
    rows: list[LeagueStandingRowOut]


class ScoreOverrideIn(BaseModel):
    score: float
    reason: str


class ContestOrganizerOut(BaseModel):
    user_id: int
    username: str
    # True for the contest's creator (created_by) - not removable here.
    is_owner: bool = False


class ContestOrganizerIn(BaseModel):
    user_id: int
