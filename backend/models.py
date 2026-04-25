from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    reset_token_hash = Column(String(64), nullable=True, index=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verify_token_hash = Column(String(64), nullable=True, index=True)
    email_verify_expires_at = Column(DateTime, nullable=True)
    # Soft lockout state for password-spray protection. Reset on every
    # successful login. ``locked_until`` is set when the user hits the
    # failure threshold; the login endpoint refuses until that moment
    # passes, without revealing whether the password was correct.
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    # For contests in solo mode, the user's affiliation is taken from this
    # column instead of their team's.
    solo_affiliation_id = Column(Integer, ForeignKey("affiliations.id", ondelete="SET NULL"), nullable=True)

    # TOTP-based 2FA. ``totp_secret`` is base32 (RFC 6238); never sent
    # to the client after enrollment except embedded in the otpauth URL
    # at setup time. ``totp_recovery_codes`` stores SHA-256 hashes of
    # 8 single-use codes the user keeps offline; each is consumed on
    # first successful use during login.
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    totp_recovery_codes = Column(Text, nullable=True)  # JSON: list[str] of sha256 hex hashes

    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="submitted_by_user")
    solo_affiliation = relationship("Affiliation", foreign_keys=[solo_affiliation_id])


class Affiliation(Base):
    """School / university / institution that teams and solo contestants
    belong to. DOMjudge calls these "organizations"; the CLICS event feed
    exposes them as ``organizations``. Purely cosmetic on the scoreboard —
    no gating or permissioning attaches to an affiliation."""
    __tablename__ = "affiliations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    short_name = Column(String(32), nullable=True)
    country_code = Column(String(3), nullable=True)  # ISO-3166 alpha-3 (e.g. BEL, USA)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    join_code = Column(String(20), unique=True, nullable=False)
    affiliation_id = Column(Integer, ForeignKey("affiliations.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    affiliation = relationship("Affiliation")

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="team", cascade="all, delete-orphan")
    # Without an explicit cascade here, deleting a team would cause SQLAlchemy
    # to UPDATE join_requests.team_id = NULL first, which fails the NOT NULL
    # constraint. cascade="all, delete-orphan" makes the ORM DELETE the
    # children itself instead of trying to null-out the FK.
    join_requests = relationship(
        "JoinRequest",
        back_populates="team",
        cascade="all, delete-orphan",
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")
    can_submit = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime, default=utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

    # A user can be in at most one team at a time.
    __table_args__ = (
        UniqueConstraint("team_id", "user_id"),
        UniqueConstraint("user_id", name="uq_team_members_user"),
    )


class Contest(Base):
    __tablename__ = "contests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    problem_statement = Column(Text, default="")
    problem_statement_pdf_path = Column(String(255), nullable=True)
    problem_statement_pdf_name = Column(String(255), nullable=True)
    # Time pipeline (each nullable; admin always bypasses every gate):
    #   visible_at   -> non-admins start seeing the contest
    #   start_time   -> submissions open ("active")
    #   end_time     -> submissions close
    #   hidden_at    -> non-admins stop seeing the contest
    # freeze_scoreboard_at freezes the non-admin scoreboard at that moment
    # and keeps it frozen until an admin clears the field. Lets the jury
    # run the reveal ceremony before the final ranking is published.
    visible_at = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    hidden_at = Column(DateTime, nullable=True)
    freeze_scoreboard_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    scoring_script = Column(Text, default="score = 0")
    # Participation mode: "team" (only teams submit), "solo" (only individuals),
    # "both" (user picks each submission). Default keeps existing behaviour.
    participation_mode = Column(String(10), default="team", nullable=False)
    # Public contests are visible/joinable by any authenticated user. Private
    # contests only show up for users in ContestParticipant.
    is_public = Column(Boolean, default=True, nullable=False)
    # Discriminator: "output" (Hashcode-style — upload an output, script grades
    # it on a numeric score) or "icpc" (source code submitted, judged against
    # testcases with AC/WA/TLE/... verdicts).
    kind = Column(String(16), default="output", nullable=False)
    # Practice mode: users can still submit after end_time, but practice
    # submissions are excluded from the official scoreboard.
    practice_mode = Column(Boolean, default=False, nullable=False)
    # Contest-scale hardening knobs (all optional; 0/null means "no limit"):
    #   dedup_block        — reject identical-hash submissions (409) instead of auditing
    #   min_seconds_between_submits — per team/solo cooldown on the same instance
    #   max_submissions_per_instance — per team/solo quota per instance
    #   output_validator_script — runs before scoring; failures mark submission
    #                             as "invalid_output" and bypass scoring entirely
    dedup_block = Column(Boolean, default=False, nullable=False)
    min_seconds_between_submits = Column(Integer, default=0, nullable=False)
    max_submissions_per_instance = Column(Integer, nullable=True)
    output_validator_script = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    instances = relationship("Instance", back_populates="contest", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="contest", cascade="all, delete-orphan")
    announcements = relationship(
        "Announcement",
        back_populates="contest",
        cascade="all, delete-orphan",
        order_by="desc(Announcement.created_at)",
    )
    hints = relationship(
        "Hint",
        back_populates="contest",
        cascade="all, delete-orphan",
        order_by="Hint.order_idx",
    )

    # Defensive DB-level guard against invalid mode/kind values that
    # bypass the Pydantic validators (manual SQL fixes, ORM inserts in
    # tests, etc.). Mirrored by an Alembic migration so prod gets it
    # too.
    __table_args__ = (
        CheckConstraint(
            "participation_mode IN ('team', 'solo', 'both')",
            name="ck_contest_participation_mode",
        ),
        CheckConstraint(
            "kind IN ('output', 'icpc')",
            name="ck_contest_kind",
        ),
    )

    @property
    def has_problem_statement_pdf(self) -> bool:
        return bool(self.problem_statement_pdf_path)


# (Team model below adds a join_requests relationship with cascade below.)


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    input_data = Column(Text, default="")
    file_path = Column(String(255), default="")
    # Two ways to define unlock: either an absolute datetime (takes priority),
    # or an offset in seconds from the contest's start_time. 0 delay = unlocks
    # at contest start.
    unlock_delay_seconds = Column(Integer, default=0, nullable=False)
    unlock_at_absolute = Column(DateTime, nullable=True)
    # Optional hard close: once the wall clock passes this, the instance
    # stops accepting submissions even if the contest is still open.
    # ``None`` = stays open as long as the contest does.
    close_at_absolute = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    contest = relationship("Contest", back_populates="instances")
    submissions = relationship("Submission", back_populates="instance", cascade="all, delete-orphan")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=utcnow, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_username = Column(String(100), default="")  # denormalised for after-delete readability
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), default="")
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, default="")

    actor = relationship("User")


class EmailOutbox(Base):
    """Durable email queue. ``email_utils._send_email`` enqueues here
    (commit-safe with the request transaction) instead of dispatching
    SMTP inline; a background worker picks rows up and sends them with
    retry. Surviving a backend restart is the whole point — the
    previous in-memory ``BackgroundTasks + retry loop`` would lose
    every queued email on a redeploy."""
    __tablename__ = "email_outbox"

    id = Column(Integer, primary_key=True, index=True)
    to_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    # ``pending`` → not yet attempted ; ``sent`` → success ;
    # ``failed`` → exhausted retries (admin can retry manually).
    status = Column(String(16), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    next_attempt_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), default="")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    contest = relationship("Contest", back_populates="announcements")
    author = relationship("User")


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    message = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    team = relationship("Team", back_populates="join_requests", foreign_keys=[team_id])
    user = relationship("User", foreign_keys=[user_id])
    decider = relationship("User", foreign_keys=[decided_by])


class ContestParticipant(Base):
    """Allowlist row for private contests — polymorphic on team_id/user_id.
    Exactly one of team_id / user_id is set depending on the contest's
    participation_mode. Absent = that entity cannot register."""
    __tablename__ = "contest_participants"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    added_at = Column(DateTime, default=utcnow)
    added_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    contest = relationship("Contest")
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_participant"),
        UniqueConstraint("contest_id", "team_id", name="uq_contest_participant_team"),
    )


class ContestRegistration(Base):
    """Self-service registration — polymorphic on team_id/user_id. A user (or
    team, via its owner) presses "Register" to opt into a contest. Non-registered
    users can still view the scoreboard but can't submit."""
    __tablename__ = "contest_registrations"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    registered_at = Column(DateTime, default=utcnow)
    registered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Disqualified registrations stay in the table (for audit trail) but
    # their submissions are filtered out of the scoreboard.
    disqualified = Column(Boolean, default=False, nullable=False)
    disqualified_reason = Column(String(255), nullable=True)

    contest = relationship("Contest")
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_registration_user"),
        UniqueConstraint("contest_id", "team_id", name="uq_contest_registration_team"),
    )


class ContestBan(Base):
    """Persistent disqualification keyed by (contest, user). Survives the
    delete of the registration row, so a banned user can't unregister
    and re-register to escape the sanction. Also catches scope-switching
    evasion: if a banned solo user joins a team, the team can't
    register for that contest because at least one member is banned.

    Created by ``set_registration_disqualified`` (one row per affected
    user — for team DQs, one row per current member). Cleared by the
    same endpoint on requalify."""
    __tablename__ = "contest_bans"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    contest = relationship("Contest")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_ban_scope"),
    )


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    # team_id is now nullable: solo submissions in a solo/both contest have no team.
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    # instance_id is nullable because ICPC submissions use problem_id instead.
    # Exactly one of instance_id or problem_id must be set per submission.
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=True)
    file_name = Column(String(255), default="")
    file_path = Column(String(255), default="")
    submission_data = Column(Text, default="")
    content_hash = Column(String(64), nullable=True, index=True)
    score = Column(Float, nullable=True)
    status = Column(String(20), default="pending")
    error_message = Column(Text, default="")
    submitted_at = Column(DateTime, default=utcnow)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # True when submitted after end_time in practice mode — excluded from the
    # official scoreboard but still scored for user feedback.
    is_practice = Column(Boolean, default=False, nullable=False)
    # Submitter's IP at upload time, for anti-cheat forensics. May be the
    # reverse-proxy IP in prod; always paired with submitted_by user id.
    submitter_ip = Column(String(64), nullable=True)
    # Hashcode-style "final" flag: user picks one submission per (team,
    # instance) and the scoreboard prefers it over the best-so-far.
    is_final = Column(Boolean, default=False, nullable=False)
    # ICPC fields (nullable; only populated for kind="icpc" submissions). A
    # Submission is either tied to (instance) for output-scoring contests or
    # to (problem) for ICPC contests. The scoring pipeline branches on which
    # column is populated.
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=True, index=True)
    source_language = Column(String(32), nullable=True)
    # Partial-credit score for subtask-mode problems. Null for plain ICPC
    # (AC/WA) — the scoreboard keeps using ``verdict`` in that case.
    total_points = Column(Float, nullable=True)
    # Captured stdout when a team submits source code for an output
    # contest (scoring kind=="output" + source_language set). The worker
    # compiles + runs the source against the instance input and writes
    # the program's stdout here; validator + scorer then consume this
    # instead of ``submission_data``, which keeps the original source
    # for the admin view.
    generated_output = Column(Text, nullable=True)

    team = relationship("Team", back_populates="submissions")
    contest = relationship("Contest", back_populates="submissions")
    instance = relationship("Instance", back_populates="submissions")
    submitted_by_user = relationship("User", back_populates="submissions")


class Hint(Base):
    __tablename__ = "hints"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(200), nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    # Fractional penalty applied to the *team/solo* total score when unlocked
    # by any member. 0 = free, 1 = zeroes the score.
    cost_fraction = Column(Float, nullable=False, default=0.1)
    order_idx = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow)

    contest = relationship("Contest", back_populates="hints")
    unlocks = relationship("HintUnlock", back_populates="hint", cascade="all, delete-orphan")


class ScoreboardEntry(Base):
    """Pre-aggregated (team or solo user, instance) best score. Updated by
    the scoring worker on every successful scoring; read by the scoreboard
    endpoint so we don't recompute the whole ladder per request.

    Exactly one of team_id / user_id is non-null. Uniqueness is enforced
    per-row via the composite unique index below."""
    __tablename__ = "scoreboard_entries"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    # "best score so far" — excludes practice submissions + errors.
    best_score = Column(Float, default=0.0, nullable=False)
    # Score of the is_final submission if any, otherwise null. Scoreboard
    # prefers this over best_score when present.
    final_score = Column(Float, nullable=True)
    submission_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "contest_id", "instance_id", "team_id", "user_id",
            name="uq_scoreboard_entry_scope",
        ),
    )


class HintUnlock(Base):
    __tablename__ = "hint_unlocks"
    __table_args__ = (
        UniqueConstraint("hint_id", "user_id", name="uq_hint_unlocks_hint_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    hint_id = Column(Integer, ForeignKey("hints.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=utcnow)

    hint = relationship("Hint", back_populates="unlocks")


# ── ICPC mode ─────────────────────────────────────────────────────────────────

class Language(Base):
    """Compile + run templates for an ICPC language. The row itself is tiny;
    the heavy lifting happens in the scoring sandbox. IDs match DOMjudge's
    short codes (``cpp``, ``java``, ``py3``, ``kotlin``…) so Kattis/DOMjudge
    package imports can map straight through."""
    __tablename__ = "languages"

    id = Column(String(32), primary_key=True)  # e.g. "py3", "cpp", "java"
    display_name = Column(String(64), nullable=False)
    # Comma-separated extensions the frontend accepts on the file picker.
    extensions = Column(String(64), nullable=False, default="")
    # Shell commands with {src}, {exe}, {mainclass} placeholders. Empty
    # compile_cmd = interpreted languages (no compile step).
    compile_cmd = Column(Text, nullable=False, default="")
    run_cmd = Column(Text, nullable=False)
    # Per-language slowdown multiplier — Java and Python get 2-3× the
    # problem's base time limit. Matches DOMjudge's wallclock_time_factor.
    time_factor = Column(Float, nullable=False, default=1.0)
    enabled = Column(Boolean, nullable=False, default=True)


class Problem(Base):
    """ICPC problem. A Contest(kind="icpc") has N problems; a Problem has M
    testcases and can ship a statement PDF."""
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    # DOMjudge "shortname" — used to round-trip imports (unique per contest).
    external_id = Column(String(64), nullable=False)
    label = Column(String(8), nullable=False)        # "A", "B", "C", ...
    color = Column(String(16), nullable=False, default="")  # scoreboard balloon
    name = Column(String(200), nullable=False)
    time_limit_ms = Column(Integer, nullable=False, default=1000)
    # 2 GB matches DOMjudge's default. The earlier 256 MB was too tight
    # for Python/Java — the interpreter alone eats hundreds of MB of
    # virtual address space once RLIMIT_AS is clamped, surfacing as MLE.
    memory_limit_mb = Column(Integer, nullable=False, default=2048)
    # Built-in checker kinds cover ~90% of Kattis problems:
    #   "diff"        — exact byte match (minus trailing whitespace)
    #   "tokens"      — whitespace-insensitive token match
    #   "float"       — tokens + per-token float tolerance (epsilon field)
    #   "custom"      — run checker_script (future; stubbed for now)
    #   "interactive" — user program + interactor_script talk via pipes;
    #                   interactor's exit code is the verdict
    checker_kind = Column(String(16), nullable=False, default="tokens")
    checker_epsilon = Column(Float, nullable=True)
    checker_script = Column(Text, nullable=True)
    # Source for the interactor. Only consulted when
    # checker_kind == "interactive". Exits 0 = AC, 42 = WA (Kattis
    # convention); any other non-zero is treated as RE.
    interactor_script = Column(Text, nullable=True)
    # Language id (matches Language.id, e.g. "py3", "cpp"). Python gets
    # the sugar wrapper (``verdict()`` helper, locals for ``testcase_input``).
    # Compiled languages read the testcase via INTERACTOR_INPUT_FILE /
    # INTERACTOR_EXPECTED_FILE env vars and speak plain stdin/stdout.
    interactor_language = Column(String(32), nullable=False, default="py3")
    # Number of times the user's program is invoked per testcase. 1 =
    # classic batch, >1 = "multi-pass" style (each run gets the original
    # input concatenated with all prior runs' outputs). Only the final
    # pass's output is checked.
    num_passes = Column(Integer, nullable=False, default=1)
    statement_pdf_path = Column(String(255), nullable=True)
    order_idx = Column(Integer, nullable=False, default=0)
    # Scoring mode:
    #   "icpc"     — binary AC/WA, short-circuit on first non-AC (default).
    #   "subtasks" — run every testcase, group by Testcase.group_name.
    #                A group scores its full points only if every testcase
    #                in it is AC. total_points on the Submission is the sum.
    scoring_mode = Column(String(16), nullable=False, default="icpc")
    created_at = Column(DateTime, default=utcnow)

    contest = relationship("Contest")
    testcases = relationship(
        "Testcase",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="Testcase.rank",
    )

    __table_args__ = (
        UniqueConstraint("contest_id", "external_id", name="uq_problem_contest_external"),
        UniqueConstraint("contest_id", "label", name="uq_problem_contest_label"),
    )


class Testcase(Base):
    """One (input, expected_output) pair for a Problem. Sample testcases are
    visible to teams in the problem view; secret testcases are used for
    judging only."""
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False, default=0)
    is_sample = Column(Boolean, nullable=False, default=False)
    # For v1 we hold input / expected_output inline; for very large datasets
    # switch to file paths later (Kattis samples are typically <10 KB each).
    input_data = Column(Text, nullable=False, default="")
    expected_output = Column(Text, nullable=False, default="")
    points = Column(Integer, nullable=False, default=1)
    # Subtask label. Testcases sharing a group_name form one subtask: the
    # subtask's points are awarded only if every case in the group is AC.
    # ``None`` means the testcase is its own one-shot group.
    group_name = Column(String(64), nullable=True)

    problem = relationship("Problem", back_populates="testcases")


class Judging(Base):
    """Result of judging one Submission against a Problem's testcases.
    One Submission has exactly one active Judging (rejudges produce a new
    row and flip is_active)."""
    __tablename__ = "judgings"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict = Column(String(8), nullable=False, default="pending")
    max_runtime_ms = Column(Integer, nullable=True)
    compile_output = Column(Text, nullable=True)
    judged_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # Jury override: admin can forcibly change the verdict (e.g. to mark a
    # borderline WA as AC after reading the diff, or to downgrade a lucky
    # AC as RE). When non-null, the override fields take precedence over
    # the original ``verdict`` in scoreboard calculations.
    override_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    override_reason = Column(Text, nullable=True)
    override_at = Column(DateTime, nullable=True)

    runs = relationship("JudgingRun", back_populates="judging", cascade="all, delete-orphan")


class JudgingRun(Base):
    """Verdict for one (Judging, Testcase) pair. Lets the UI show a per-case
    grid and lets the jury diagnose partial failures."""
    __tablename__ = "judging_runs"

    id = Column(Integer, primary_key=True, index=True)
    judging_id = Column(Integer, ForeignKey("judgings.id", ondelete="CASCADE"), nullable=False, index=True)
    testcase_id = Column(Integer, ForeignKey("testcases.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict = Column(String(8), nullable=False, default="pending")
    runtime_ms = Column(Integer, nullable=True)
    memory_used_mb = Column(Integer, nullable=True)
    # Truncated stdout/stderr (first ~1 KB) for the jury view. Full output
    # is discarded — we don't want to retain arbitrary team-controlled data.
    stdout_truncated = Column(Text, nullable=True)
    stderr_truncated = Column(Text, nullable=True)

    judging = relationship("Judging", back_populates="runs")
    testcase = relationship("Testcase")


class Clarification(Base):
    """Q&A between teams and jury during an ICPC contest. Team asks, jury
    answers; answer can be ``public`` (broadcast to all teams) or
    ``private`` (visible only to the asking team)."""
    __tablename__ = "clarifications"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    from_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    answered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answered_at = Column(DateTime, nullable=True)
    visibility = Column(String(16), nullable=False, default="private")  # "public" | "private"
    created_at = Column(DateTime, default=utcnow)


class IcpcScoreboardEntry(Base):
    """Materialised (team, problem) cell for the ICPC scoreboard — the
    penalty-time layout is too different from the output-scoring cache to
    share. Updated by the judging worker on every finished Judging."""
    __tablename__ = "icpc_scoreboard_entries"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    solved = Column(Boolean, nullable=False, default=False)
    # Wrong / TLE / RE attempts BEFORE the first AC. Each counts 20 min penalty.
    attempts_before_ac = Column(Integer, nullable=False, default=0)
    # Total attempts (for display). Counts every non-pending judging.
    attempts_total = Column(Integer, nullable=False, default=0)
    # Minutes from contest start to first AC.
    first_solve_minutes = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "contest_id", "team_id", "user_id", "problem_id",
            name="uq_icpc_scoreboard_scope",
        ),
    )


