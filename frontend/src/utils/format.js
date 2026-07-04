const UNITS = [
  { v: 1e18, s: 'E' },
  { v: 1e15, s: 'P' },
  { v: 1e12, s: 'T' },
  { v: 1e9, s: 'B' },
  { v: 1e6, s: 'M' },
  { v: 1e3, s: 'K' },
];

export function formatScore(value) {
  if (value == null) return '-';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return '-';

  const abs = Math.abs(n);
  if (abs < 1000) return n.toFixed(1);

  if (abs < 1e21) {
    for (const u of UNITS) {
      if (abs >= u.v) {
        const r = n / u.v;
        const ar = Math.abs(r);
        const d = ar >= 100 ? 0 : ar >= 10 ? 1 : 2;
        return r.toFixed(d) + u.s;
      }
    }
  }

  return n.toExponential(2).replace('e+', 'e');
}

export function formatScoreFull(value) {
  if (value == null) return '-';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return '-';

  const abs = Math.abs(n);
  if (abs >= 1e16) return n.toExponential(6).replace('e+', 'e');
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

export function clampRatio(numerator, denominator) {
  const num = Number(numerator);
  const den = Number(denominator);
  if (!Number.isFinite(num) || !Number.isFinite(den) || den <= 0) return 0;
  const r = num / den;
  if (!Number.isFinite(r) || r <= 0) return 0;
  return r > 1 ? 1 : r;
}
