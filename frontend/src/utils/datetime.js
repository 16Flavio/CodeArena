// Helpers bridging <input type="datetime-local"> (always naive local time)
// and the backend's UTC ISO strings.

// Backend returns naive datetimes (e.g. "2026-04-20T14:00:00") that represent
// UTC. Without this, new Date() would interpret them as local time and the
// value would drift by the user's UTC offset on every edit round-trip.
export function parseBackendIso(iso) {
  if (!iso) return null;
  const hasTz = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(hasTz ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function backendIsoMs(iso) {
  const d = parseBackendIso(iso);
  return d ? d.getTime() : null;
}

export function toUtcIso(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export function toLocalInputValue(iso) {
  const d = parseBackendIso(iso);
  if (!d) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export function formatDateTime(iso, locale = 'fr-FR') {
  const d = parseBackendIso(iso);
  if (!d) return '';
  return d.toLocaleString(locale, {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

// Format a duration (in seconds) as a compact, human-friendly string.
// Used for "instance unlocks in 42:31".
export function formatCountdown(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (days > 0) return `${days}j ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
  return `${minutes}m ${String(secs).padStart(2, '0')}s`;
}
