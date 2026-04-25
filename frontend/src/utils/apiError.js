// Single error-rendering helper for axios responses.
//
// Backend sends two formats:
//   1. Legacy:  { detail: "Some French string" }
//   2. Coded:   { detail: { code, message, params? } }
//
// The coded format is preferred — it lets us i18n the user-visible
// string per language. Older sites still pass strings; the helper
// renders them verbatim.

import { i18n } from '../i18n/index.js';

// Code → translation key. Adding a new error code means adding one
// row here and one entry per locale in i18n/{fr,en}.json under
// ``errors.<code>``. The fallback path uses the backend's English
// ``message`` field when the code is unknown.
const CODE_TO_KEY = {
  INVALID_CREDENTIALS: 'errors.invalidCredentials',
  ACCOUNT_LOCKED: 'errors.accountLocked',
  EMAIL_NOT_VERIFIED: 'errors.emailNotVerified',
  USERNAME_TAKEN: 'errors.usernameTaken',
  EMAIL_TAKEN: 'errors.emailTaken',
  TOTP_REQUIRED: 'errors.totpRequired',
  TOTP_INVALID: 'errors.totpInvalid',
  TOTP_ALREADY_ENABLED: 'errors.totpAlreadyEnabled',
  TOTP_NOT_ENABLED: 'errors.totpNotEnabled',
  CONTEST_NOT_FOUND: 'errors.contestNotFound',
  CONTEST_NOT_OPEN: 'errors.contestNotOpen',
  NOT_REGISTERED: 'errors.notRegistered',
  ALREADY_REGISTERED: 'errors.alreadyRegistered',
  REGISTRATION_DISQUALIFIED: 'errors.registrationDisqualified',
  BANNED_FROM_CONTEST: 'errors.bannedFromContest',
  NOT_ON_ALLOWLIST: 'errors.notOnAllowlist',
  SUBMISSION_DUPLICATE: 'errors.submissionDuplicate',
  SUBMISSION_TOO_LARGE: 'errors.submissionTooLarge',
  SUBMISSION_COOLDOWN: 'errors.submissionCooldown',
  SUBMISSION_QUOTA_EXCEEDED: 'errors.submissionQuotaExceeded',
  INSTANCE_LOCKED: 'errors.instanceLocked',
  NOT_FOUND: 'errors.notFound',
  FORBIDDEN: 'errors.forbidden',
};

export function extractErrorMessage(err, fallback = '') {
  const detail = err?.response?.data?.detail;
  if (detail == null) return fallback;
  if (typeof detail === 'string') return detail;
  // Structured payload: { code, message, params? }
  if (typeof detail === 'object') {
    const key = CODE_TO_KEY[detail.code];
    if (key && i18n.exists(key)) {
      return i18n.t(key, detail.params || {});
    }
    // Unknown code → use the backend's English message verbatim
    // so the user gets something meaningful instead of "[object Object]".
    if (detail.message) {
      // Append a non-empty params.reason if the backend included one
      // — DQ errors carry the admin's free-form reason there.
      if (detail.params?.reason) {
        return `${detail.message} — ${detail.params.reason}`;
      }
      return detail.message;
    }
  }
  return fallback;
}
