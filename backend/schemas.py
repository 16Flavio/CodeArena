from pydantic import BaseModel, EmailStr, field_validator, model_validator


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


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
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
    team_id: int
    team_name: str
    contest_id: int
    contest_title: str
    rank: int
    total_teams: int
    total_score: float


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
    # by unregistering — only an admin can.
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
    # output-scoring — they use ``status`` + ``score`` instead.
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
    kind: str  # "announcement" | "team_submission"
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
    order_idx: int = 0
    has_statement_pdf: bool = False
    sample_testcases: list[TestcaseOut] = []
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
    runtime_ms: Optional[int] = None
    is_sample: bool = False
    # First ~1 KB of the program's stdout + stderr on this testcase. Only
    # populated for the submitter / teammates / admin (same authz as the
    # surrounding judging response).
    stdout_truncated: Optional[str] = None
    stderr_truncated: Optional[str] = None


class TestcaseOutline(BaseModel):
    """Identity-only view of a Testcase — id, ordering, and whether it's a
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
    """Per-instance "winner" for the scoring presentation — the team
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
