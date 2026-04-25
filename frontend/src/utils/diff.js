// Minimal line-based diff using an LCS table. Returns an array of
// { kind: 'same' | 'add' | 'del', left, right } rows suitable for rendering
// side-by-side. Large inputs are truncated — this is for glance comparisons,
// not a Git-grade engine.
const MAX_LINES = 4000;

export function diffLines(aText, bText) {
  const aAll = (aText || '').split('\n');
  const bAll = (bText || '').split('\n');
  const aLines = aAll.slice(0, MAX_LINES);
  const bLines = bAll.slice(0, MAX_LINES);
  const n = aLines.length;
  const m = bLines.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      if (aLines[i] === bLines[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (aLines[i] === bLines[j]) {
      out.push({ kind: 'same', left: aLines[i], right: bLines[j] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ kind: 'del', left: aLines[i], right: null });
      i += 1;
    } else {
      out.push({ kind: 'add', left: null, right: bLines[j] });
      j += 1;
    }
  }
  while (i < n) {
    out.push({ kind: 'del', left: aLines[i], right: null });
    i += 1;
  }
  while (j < m) {
    out.push({ kind: 'add', left: null, right: bLines[j] });
    j += 1;
  }
  if (aAll.length > MAX_LINES || bAll.length > MAX_LINES) {
    out.push({ kind: 'same', left: '[…truncated]', right: '[…truncated]' });
  }
  return out;
}
