import { useEffect, useRef } from 'react';
import { getStreamTicket, scoreboardStreamUrl } from '../api';

// Live scoreboard over Server-Sent Events, shared by the output-scoring
// (`pages/Scoreboard.jsx`) and ICPC (`components/IcpcScoreboard.jsx`) boards.
//
// Both used to inline this, and both carried the same bug: `onerror` called
// `source.close()`, which permanently disables EventSource's built-in
// reconnect, then did exactly one manual refetch. So the first hiccup - a
// proxy read timeout, a backend redeploy, a laptop waking from sleep - froze
// the "live" board until the user pressed F5, with no visible sign that it
// had stopped updating.
//
// Closing is actually right here (the auth ticket is short-lived, so the
// browser's own reconnect would just 401), but it has to be paired with a
// fresh handshake. That's what this hook does: reconnect with exponential
// backoff, refresh once through the plain GET on every attempt so the board
// stays warm meanwhile, and reset the backoff as soon as a message lands.

const BASE_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;
// Used only when the browser has no EventSource at all.
const FALLBACK_POLL_MS = 10_000;

export default function useScoreboardStream({
  contestId,
  enabled,
  onPayload,
  onFallbackRefresh,
}) {
  // Callbacks live in refs so a re-render doesn't tear down the stream:
  // the effect must only depend on the contest and the on/off switch.
  const payloadRef = useRef(onPayload);
  const refreshRef = useRef(onFallbackRefresh);
  // Assigned in an effect, not during render: the callers pass fresh arrow
  // functions every render, and writing a ref mid-render is a purity break.
  useEffect(() => {
    payloadRef.current = onPayload;
    refreshRef.current = onFallbackRefresh;
  });

  useEffect(() => {
    if (!enabled || !contestId) return undefined;

    let cancelled = false;
    let source = null;
    let retryTimer = null;
    let pollTimer = null;
    let attempt = 0;

    // No EventSource (old browser, some embedded webviews): plain polling.
    if (typeof EventSource === 'undefined') {
      refreshRef.current?.();
      pollTimer = setInterval(() => refreshRef.current?.(), FALLBACK_POLL_MS);
      return () => clearInterval(pollTimer);
    }

    const closeSource = () => {
      if (!source) return;
      source.onmessage = null;
      source.onerror = null;
      source.close();
      source = null;
    };

    const scheduleReconnect = () => {
      if (cancelled || retryTimer) return;
      // Keep the board fresh while we wait for the next handshake.
      refreshRef.current?.();
      const delay = Math.min(BASE_BACKOFF_MS * 2 ** attempt, MAX_BACKOFF_MS);
      attempt += 1;
      retryTimer = setTimeout(() => {
        retryTimer = null;
        connect();
      }, delay);
    };

    const connect = () => {
      if (cancelled) return;
      // A short-lived (60s) ticket, because EventSource cannot set headers
      // and we refuse to put the durable session token in a URL.
      getStreamTicket()
        .then((r) => {
          if (cancelled) return;
          const url = `${scoreboardStreamUrl(contestId)}?token=${encodeURIComponent(r.data.ticket)}`;
          source = new EventSource(url, { withCredentials: false });

          source.onmessage = (e) => {
            attempt = 0; // healthy stream - forget the previous failures
            try {
              payloadRef.current?.(JSON.parse(e.data));
            } catch {
              /* malformed event; ignore rather than kill the stream */
            }
          };

          source.onerror = (e) => {
            // Two different things arrive here. The backend emits a named
            // `event: error` (carrying data) when the contest is gone or
            // hidden - permanent, so retrying would just hammer it. A
            // transport failure has no data and deserves a reconnect.
            const isServerError = !!(e && e.data);
            closeSource();
            if (isServerError) {
              refreshRef.current?.(); // let the plain GET surface the reason
              return;
            }
            scheduleReconnect();
          };
        })
        .catch(() => {
          if (cancelled) return;
          scheduleReconnect();
        });
    };

    connect();

    // Browsers and proxies drop streams held by a backgrounded tab. Coming
    // back to the tab should reconnect now, not after the backoff expires.
    const onVisibility = () => {
      if (cancelled || document.visibilityState !== 'visible') return;
      if (source) return; // still connected
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      attempt = 0;
      connect();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', onVisibility);
      if (retryTimer) clearTimeout(retryTimer);
      if (pollTimer) clearInterval(pollTimer);
      closeSource();
    };
  }, [contestId, enabled]);
}
