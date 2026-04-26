import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..errors import ErrorCode, raise_error
from ..email_utils import send_password_reset_email, send_email_verification
from ..rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_HOURS = 1

# Minimum policy. Conservative thresholds rather than something
# zxcvbn-grade: we want a real floor (10 chars + diversity) without
# imposing rules that frustrate users (mandatory symbols, frequent
# rotation). The blocklist catches the absolute worst (top-of-leaks
# passwords) so users who paste "password123" get rejected at register
# time. Frontend has a strength meter — backend is the ultimate gate.
PASSWORD_MIN_LENGTH = 10
_PASSWORD_BLOCKLIST = frozenset(
    p.lower() for p in (
        "password", "password1", "password123", "password1234",
        "qwerty", "qwerty123", "azerty", "azerty123",
        "12345678", "123456789", "1234567890",
        "letmein", "letmein123",
        "welcome1", "welcome123",
        "admin", "admin123", "administrator",
        "iloveyou", "monkey123", "abc12345",
        "codearena", "codearena1", "codearena123",
    )
)


def _check_password_policy(password: str) -> None:
    """Raise HTTPException 400 if ``password`` doesn't meet the policy.
    Called by register / change-password / reset-password so all three
    surfaces share one rule."""
    pw = password or ""
    if len(pw) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères",
        )
    has_letter = any(c.isalpha() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    if not (has_letter and has_digit):
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir au moins une lettre et un chiffre",
        )
    if pw.lower() in _PASSWORD_BLOCKLIST:
        raise HTTPException(
            status_code=400,
            detail="Ce mot de passe est trop courant. Choisissez-en un autre.",
        )


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/register", response_model=schemas.UserOut)
@limiter.limit("5/minute")
def register(
    request: Request,
    data: schemas.UserRegister,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise_error(
            code=ErrorCode.USERNAME_TAKEN,
            status=400,
            message="This username is already taken",
        )
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise_error(
            code=ErrorCode.EMAIL_TAKEN,
            status=400,
            message="This email is already registered",
        )
    _check_password_policy(data.password)

    is_first_user = db.query(models.User).count() == 0
    user = models.User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        is_admin=is_first_user,
        # First user (admin) is trusted automatically.
        email_verified=is_first_user,
    )
    # Stash a verification token for non-first users.
    if not is_first_user:
        raw = secrets.token_urlsafe(32)
        user.email_verify_token_hash = _hash_token(raw)
        user.email_verify_expires_at = _utcnow() + timedelta(days=3)
        db.add(user)
        db.commit()
        db.refresh(user)
        background.add_task(send_email_verification, user.email, raw)
    else:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/verify-email", response_model=schemas.SimpleMessage)
def verify_email(data: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    if not data.token:
        raise HTTPException(status_code=400, detail="Jeton manquant")
    token_hash = _hash_token(data.token)
    user = (
        db.query(models.User)
        .filter(models.User.email_verify_token_hash == token_hash)
        .first()
    )
    expires = user.email_verify_expires_at if user else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not user or not expires or expires < _utcnow():
        raise HTTPException(status_code=400, detail="Lien de vérification invalide ou expiré")
    user.email_verified = True
    user.email_verify_token_hash = None
    user.email_verify_expires_at = None
    db.commit()
    return {"detail": "Email vérifié. Merci !"}


@router.post("/resend-verification", response_model=schemas.SimpleMessage)
@limiter.limit("3/hour")
def resend_verification(
    request: Request,
    background: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.email_verified:
        return {"detail": "Email déjà vérifié."}
    raw = secrets.token_urlsafe(32)
    user.email_verify_token_hash = _hash_token(raw)
    user.email_verify_expires_at = _utcnow() + timedelta(days=3)
    db.commit()
    background.add_task(send_email_verification, user.email, raw)
    return {"detail": "Nouvel email de vérification envoyé."}


@router.post("/change-username", response_model=schemas.UserOut)
@limiter.limit("5/hour")
def change_username(
    request: Request,
    data: schemas.ChangeUsernameRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    new_name = (data.new_username or "").strip()
    if len(new_name) < 2 or len(new_name) > 50:
        raise HTTPException(status_code=400, detail="Le nom d'utilisateur doit faire entre 2 et 50 caractères")
    if new_name == user.username:
        raise HTTPException(status_code=400, detail="Le nouveau nom d'utilisateur doit être différent")
    if db.query(models.User).filter(models.User.username == new_name).first():
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà pris")
    user.username = new_name
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", response_model=schemas.SimpleMessage)
@limiter.limit("10/hour")
def change_password(
    request: Request,
    data: schemas.ChangePasswordRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    _check_password_policy(data.new_password)
    if data.new_password == data.current_password:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit être différent de l'ancien")
    user.password_hash = hash_password(data.new_password)
    # The lockout counter is shared between password and 2FA failures.
    # If the legitimate user just changed their password, any prior
    # bad-attempt streak is moot — clear it so they're not surprised
    # by a 15-minute lockout the first time they mistype.
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return {"detail": "Mot de passe mis à jour."}


LOCKOUT_THRESHOLD = 5      # consecutive failed attempts
LOCKOUT_DURATION = 15 * 60  # seconds


@router.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()
    now = datetime.now(timezone.utc)

    # Refuse early if the account is locked, *before* touching the hash
    # — same response shape as a wrong password, so we don't leak "this
    # username exists, it's just locked" to scanners.
    if user is not None and user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            retry_s = int((locked_until - now).total_seconds())
            raise_error(
                code=ErrorCode.ACCOUNT_LOCKED,
                status=429,
                message=f"Account temporarily locked. Retry in {retry_s}s.",
                params={"retry_seconds": retry_s},
                headers={"Retry-After": str(retry_s)},
            )

    if not user or not verify_password(data.password, user.password_hash):
        # Count the failure and maybe set the lockout. Done on the User
        # row so it survives restarts and scales across backend replicas.
        if user is not None:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= LOCKOUT_THRESHOLD:
                user.locked_until = now + timedelta(seconds=LOCKOUT_DURATION)
                # Reset the counter so the next burst starts fresh after
                # the lockout window — avoids a cascading permanent lock
                # when a legitimate user forgets their password twice.
                user.failed_login_count = 0
            db.commit()
        raise_error(
            code=ErrorCode.INVALID_CREDENTIALS,
            status=401,
            message="Invalid username or password",
        )

    # Successful login: clear the counters.
    if user.failed_login_count or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()

    # If the user enabled 2FA, the password alone isn't enough — return
    # a short-lived challenge that proves "step 1 passed" so the
    # follow-up call to /2fa/login-verify doesn't have to re-check the
    # password. The challenge encodes the user_id + a TTL of 5 minutes.
    if user.totp_enabled:
        challenge = create_access_token(
            {"sub": str(user.id), "purpose": "totp_challenge", "remember_me": bool(data.remember_me)},
            expires_delta=timedelta(minutes=5),
        )
        # Status 401 with code TOTP_REQUIRED — the frontend swaps the
        # password form for a code-input form on this code.
        raise_error(
            code=ErrorCode.TOTP_REQUIRED,
            status=401,
            message="Two-factor code required",
            params={"challenge_token": challenge},
        )

    ttl = timedelta(days=30) if data.remember_me else None
    token = create_access_token({"sub": str(user.id)}, expires_delta=ttl)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/2fa/login-verify", response_model=schemas.Token)
@limiter.limit("5/minute")  # Defence-in-depth on top of the per-user lockout.
def totp_login_verify(
    request: Request,
    data: schemas.TotpLoginVerifyIn,
    db: Session = Depends(get_db),
):
    """Step 2 of the 2FA login flow. The client gets ``challenge_token``
    from the failed /login call (with code TOTP_REQUIRED), prompts the
    user for a 6-digit TOTP or a recovery code, and submits both here."""
    from jose import JWTError, jwt as _jwt
    from .. import totp as _totp
    # Read the signing key from the auth module (NOT os.environ): the
    # module sets a per-process random fallback when SECRET_KEY is
    # missing, and the encoder uses *that* to sign. Reading os.environ
    # here would diverge from the encoder, breaking 2FA verification
    # entirely on boxes without SECRET_KEY set.
    from ..auth import SECRET_KEY, ALGORITHM
    try:
        payload = _jwt.decode(data.challenge_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise_error(
            code=ErrorCode.TOTP_INVALID,
            status=400,
            message="Challenge expired or invalid — restart login",
        )
    if payload.get("purpose") != "totp_challenge":
        raise_error(
            code=ErrorCode.TOTP_INVALID,
            status=400,
            message="Invalid challenge token",
        )
    user_id = int(payload.get("sub") or 0)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.totp_enabled:
        raise_error(
            code=ErrorCode.TOTP_NOT_ENABLED,
            status=400,
            message="2FA is no longer enabled — restart login",
        )

    # Same lockout as /login: a wrong 2FA code increments the same
    # counter and triggers the same 15-minute lockout. Without this,
    # a 6-digit code is brute-forceable in ~17h at 10/min — and the
    # IP-based slowapi limit doesn't help against a botnet.
    now = datetime.now(timezone.utc)
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            retry_s = int((locked_until - now).total_seconds())
            raise_error(
                code=ErrorCode.ACCOUNT_LOCKED,
                status=429,
                message=f"Account temporarily locked. Retry in {retry_s}s.",
                params={"retry_seconds": retry_s},
                headers={"Retry-After": str(retry_s)},
            )

    code = (data.code or "").strip()
    # TOTP first (cheaper), then recovery code (consumes one).
    matched = False
    if _totp.verify_code(user.totp_secret, code):
        matched = True
    else:
        new_recovery = _totp.consume_recovery_code(user.totp_recovery_codes, code)
        if new_recovery is not None:
            user.totp_recovery_codes = new_recovery
            matched = True

    if not matched:
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(seconds=LOCKOUT_DURATION)
            user.failed_login_count = 0
        db.commit()
        raise_error(
            code=ErrorCode.TOTP_INVALID,
            status=400,
            message="Invalid 2FA code",
        )

    # Success — clear the counters from any prior failures.
    if user.failed_login_count or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None
    db.commit()

    remember = bool(payload.get("remember_me"))
    ttl = timedelta(days=30) if remember else None
    token = create_access_token({"sub": str(user.id)}, expires_delta=ttl)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=schemas.SimpleMessage)
@limiter.limit("5/hour")
def forgot_password(
    request: Request,
    data: schemas.ForgotPasswordRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    generic_reply = {
        "detail": "Si cet email est enregistré, un lien de réinitialisation a été envoyé.",
    }
    email = (data.email or "").strip().lower()
    if not email:
        return generic_reply

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )
    if not user:
        # Avoid leaking which emails are registered.
        return generic_reply

    raw_token = secrets.token_urlsafe(32)
    user.reset_token_hash = _hash_token(raw_token)
    user.reset_token_expires_at = _utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    db.commit()

    # Send email in the background so the response is always fast
    # and timing doesn't reveal whether the email existed.
    background.add_task(send_password_reset_email, user.email, raw_token)

    return generic_reply


@router.post("/reset-password", response_model=schemas.SimpleMessage)
@limiter.limit("10/hour")
def reset_password(
    request: Request,
    data: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if not data.token or not data.new_password:
        raise HTTPException(status_code=400, detail="Le jeton et le nouveau mot de passe sont requis")
    _check_password_policy(data.new_password)

    token_hash = _hash_token(data.token)
    user = (
        db.query(models.User)
        .filter(models.User.reset_token_hash == token_hash)
        .first()
    )

    now = _utcnow()
    expires_at = user.reset_token_expires_at if user else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not user or not expires_at or expires_at < now:
        raise HTTPException(status_code=400, detail="Lien de réinitialisation invalide ou expiré")

    user.password_hash = hash_password(data.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    # Clear the lockout counter — the original purpose of password
    # reset is "I forgot mine", and an attacker who's been spraying
    # passwords against this account has just been deprecated. Without
    # this, a legitimate reset still leaves the user locked out for up
    # to 15 minutes, which is precisely the DoS vector flagged in the
    # audit. (Same rationale as change-password above.)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    return {"detail": "Mot de passe mis à jour. Vous pouvez maintenant vous connecter."}


# ─── 2FA (TOTP) ──────────────────────────────────────────────────────────────
#
# Three-stage flow:
#   1. POST /2fa/setup      → generate secret, return otpauth URL.
#                             Status: enrollment in progress (totp_enabled
#                             stays False until step 2).
#   2. POST /2fa/verify     → user submits the first valid code from
#                             their authenticator app. We persist the
#                             secret + flip totp_enabled. Returns the
#                             one-time recovery codes (only chance the
#                             user has to copy them).
#   3. POST /2fa/disable    → requires current password + valid OTP or
#                             recovery code. Wipes all TOTP state.
#
# The login endpoint itself is NOT yet 2FA-aware in this scaffold —
# enabling it on the existing flow needs a challenge-token round-trip
# that affects every login client. Tracked as the next-step gap.

from .. import totp as _totp


@router.post("/2fa/setup", response_model=schemas.TotpSetupOut)
@limiter.limit("5/hour")
def totp_setup(
    request: Request,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.totp_enabled:
        raise_error(
            code=ErrorCode.TOTP_ALREADY_ENABLED,
            status=400,
            message="2FA is already enabled — disable it first if you want a new secret",
        )
    secret = _totp.generate_secret()
    user.totp_secret = secret
    # Don't flip totp_enabled until verify() succeeds; otherwise a
    # crash mid-enrollment locks the user out.
    db.commit()
    return schemas.TotpSetupOut(
        secret=secret,
        otpauth_url=_totp.otpauth_url(secret, account_name=user.email),
    )


@router.post("/2fa/verify", response_model=schemas.TotpVerifyOut)
@limiter.limit("10/hour")
def totp_verify(
    request: Request,
    data: schemas.TotpVerifyIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.totp_enabled:
        raise_error(
            code=ErrorCode.TOTP_ALREADY_ENABLED,
            status=400,
            message="2FA is already enabled",
        )
    if not user.totp_secret:
        raise_error(
            code=ErrorCode.TOTP_NOT_ENABLED,
            status=400,
            message="Run /2fa/setup first",
        )
    if not _totp.verify_code(user.totp_secret, data.code):
        raise_error(
            code=ErrorCode.TOTP_INVALID,
            status=400,
            message="Invalid 2FA code",
        )
    plaintext_codes, hashes_json = _totp.generate_recovery_codes()
    user.totp_enabled = True
    user.totp_recovery_codes = hashes_json
    db.commit()
    return schemas.TotpVerifyOut(recovery_codes=plaintext_codes)


@router.post("/2fa/disable", response_model=schemas.SimpleMessage)
@limiter.limit("5/hour")
def totp_disable(
    request: Request,
    data: schemas.TotpDisableIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.totp_enabled:
        raise_error(
            code=ErrorCode.TOTP_NOT_ENABLED,
            status=400,
            message="2FA is not enabled on this account",
        )
    if not verify_password(data.password, user.password_hash):
        raise_error(
            code=ErrorCode.INVALID_CREDENTIALS,
            status=400,
            message="Current password is incorrect",
        )
    # Either a current OTP or a recovery code accepted as proof of
    # device possession. Recovery code is consumed (matches the login
    # flow's eventual contract).
    code = (data.code or "").strip()
    ok = _totp.verify_code(user.totp_secret, code)
    if not ok:
        new_recovery = _totp.consume_recovery_code(user.totp_recovery_codes, code)
        if new_recovery is None:
            raise_error(
                code=ErrorCode.TOTP_INVALID,
                status=400,
                message="Invalid 2FA code or recovery code",
            )
        # We're disabling anyway, so the trimmed list doesn't matter —
        # just clear everything.
        used_recovery = True
    else:
        used_recovery = False
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_recovery_codes = None
    db.commit()
    # Notify the account owner — disabling 2FA is high-impact, and a
    # recovery-code-based disable means an attacker holding a leaked
    # recovery code could silently undo the protection. The user must
    # see this email and act if it wasn't them.
    try:
        from .. import email_utils as _email
        method = "code de récupération" if used_recovery else "code TOTP"
        _email._send_email(
            user.email,
            subject="CodeArena : 2FA désactivée sur votre compte",
            body=(
                "Bonjour,\n\n"
                f"L'authentification à deux facteurs (2FA) vient d'être désactivée "
                f"sur votre compte CodeArena (méthode : {method}).\n\n"
                "Si ce n'est PAS vous, votre compte est probablement compromis :\n"
                "1. Changez immédiatement votre mot de passe.\n"
                "2. Réactivez la 2FA depuis la page Sécurité.\n"
                "3. Contactez un administrateur.\n"
            ),
        )
    except Exception:  # pragma: no cover — email is best-effort
        pass
    return {"detail": "2FA disabled"}
