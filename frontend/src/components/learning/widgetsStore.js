import { learnListWidgets } from '../../api';

// Module-level cache for the DB-backed widgets. Populated on first
// LessonMarkdown render and re-used across every lesson view in the
// session. Refresh by calling ``invalidate()`` (the admin editor does
// after a save so the next render picks up the new template).

let cache = null;
let inflight = null;
// Bumped by ``invalidate()`` so a fetch that was already inflight when
// the admin saved cannot repopulate the cache with pre-save data.
let generation = 0;
const subscribers = new Set();

export async function loadWidgets() {
  if (cache) return cache;
  if (!inflight) {
    const gen = generation;
    inflight = learnListWidgets().then((r) => {
      if (gen !== generation) return cache || [];
      cache = r.data || [];
      inflight = null;
      subscribers.forEach((cb) => {
        try { cb(cache); } catch { /* ignore subscriber errors */ }
      });
      return cache;
    }).catch((err) => {
      if (gen === generation) inflight = null;
      // Fail open for THIS caller, but leave the cache empty so the
      // next render retries instead of freezing every custom widget
      // on a transient network error for the rest of the session.
      console.warn('learn widgets fetch failed:', err);
      return [];
    });
  }
  return inflight;
}

export function invalidate() {
  generation += 1;
  cache = null;
  inflight = null;
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
