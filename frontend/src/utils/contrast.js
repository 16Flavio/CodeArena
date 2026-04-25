// Pick a text colour (black or white) that stays readable on top of an
// arbitrary background. Used for the problem-label badges / balloons on
// the scoreboard — balloons come in every colour and a few pastel ones
// (pink, cyan, light grey) are illegible in white text.
//
// Formula: relative luminance from WCAG (0.299 R + 0.587 G + 0.114 B is
// the classic sRGB luminance approximation). We compare against 0.55
// instead of 0.5 so mid-tones like DOMjudge's #808080 land on black
// text, which reads better on the typical grey balloons.

export function textOn(bg) {
  const m = typeof bg === 'string' && /^#?([0-9a-f]{6}|[0-9a-f]{3})$/i.exec(bg.trim());
  if (!m) return '#ffffff';
  let hex = m[1];
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
  const r = parseInt(hex.slice(0, 2), 16) / 255;
  const g = parseInt(hex.slice(2, 4), 16) / 255;
  const b = parseInt(hex.slice(4, 6), 16) / 255;
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  return lum > 0.55 ? '#000000' : '#ffffff';
}
