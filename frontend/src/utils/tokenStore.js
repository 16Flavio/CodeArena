// Central place for JWT storage so auth state isn't accidentally
// persisted in localStorage (which survives tab close and lets a later
// visitor on a shared browser auto-log-in as the previous user).
//
// Policy: sessionStorage by default (cleared on tab close); localStorage
// only when the user ticked "remember me" at login. `get()` reads both
// and prefers sessionStorage so an active tab's token wins over a stale
// persistent one.

const KEY = 'token';
// Marker written next to the token whenever the user explicitly opted
// into "remember me". Lets the AuthContext bootstrap distinguish a
// legitimately-persistent token (keep it) from a legacy localStorage
// token left over by the pre-dual-storage build (purge it — see the
// shared-browser inheritance bug that motivated the dual scheme).
export const PERSIST_FLAG = 'token_persistent';

export function getToken() {
  try {
    return sessionStorage.getItem(KEY) || localStorage.getItem(KEY) || null;
  } catch {
    return null;
  }
}

// True iff the token lives in persistent (localStorage) storage. Used
// by flows that need to rewrite the token (e.g. after change-username)
// without accidentally demoting a "remember me" session to tab-scoped.
export function tokenIsPersistent() {
  try {
    return !!localStorage.getItem(KEY);
  } catch {
    return false;
  }
}

export function setToken(token, { remember = false } = {}) {
  try {
    if (remember) {
      localStorage.setItem(KEY, token);
      localStorage.setItem(PERSIST_FLAG, '1');
      sessionStorage.removeItem(KEY);
    } else {
      sessionStorage.setItem(KEY, token);
      localStorage.removeItem(KEY);
      localStorage.removeItem(PERSIST_FLAG);
    }
  } catch { /* storage disabled */ }
}

export function clearToken() {
  try {
    sessionStorage.removeItem(KEY);
    localStorage.removeItem(KEY);
    localStorage.removeItem(PERSIST_FLAG);
  } catch { /* ignore */ }
}
