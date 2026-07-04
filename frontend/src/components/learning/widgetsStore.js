import { learnListWidgets } from '../../api';

// Module-level cache for the DB-backed widgets. Populated on first
// LessonMarkdown render and re-used across every lesson view in the
// session. Refresh by calling ``invalidate()`` (the admin editor does
// after a save so the next render picks up the new template).

let cache = null;
let inflight = null;
const subscribers = new Set();

export async function loadWidgets() {
  if (cache) return cache;
  if (!inflight) {
    inflight = learnListWidgets().then((r) => {
      cache = r.data || [];
      inflight = null;
      subscribers.forEach((cb) => {
        try { cb(cache); } catch { /* ignore subscriber errors */ }
      });
      return cache;
    }).catch((err) => {
      inflight = null;
      // Fail open - return an empty list rather than crashing the
      // lesson reader if the widgets endpoint is down.
      console.warn('learn widgets fetch failed:', err);
      cache = [];
      return cache;
    });
  }
  return inflight;
}

export function invalidate() {
  cache = null;
  // Re-fetch immediately so the admin's "save" is visible without
  // waiting for the next lesson navigation.
  loadWidgets();
}

export function getCachedSync() {
  return cache;
}

export function subscribe(cb) {
  subscribers.add(cb);
  return () => subscribers.delete(cb);
}
