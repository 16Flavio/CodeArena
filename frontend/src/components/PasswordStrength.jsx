import { useTranslation } from 'react-i18next';

export function scorePassword(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score += 1;
  if (pw.length >= 12) score += 1;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score += 1;
  if (/\d/.test(pw)) score += 1;
  if (/[^\w\s]/.test(pw)) score += 1;
  return Math.min(score, 4);
}

const BAR_COLORS = [
  'bg-zinc-200 dark:bg-zinc-700',
  'bg-red-500',
  'bg-amber-500',
  'bg-sky-500',
  'bg-emerald-500',
];

const LABEL_KEYS = [
  'passwordStrength.none',
  'passwordStrength.weak',
  'passwordStrength.fair',
  'passwordStrength.strong',
  'passwordStrength.excellent',
];

export default function PasswordStrength({ password }) {
  const { t } = useTranslation();
  const score = scorePassword(password || '');
  if (!password) return null;
  return (
    <div className="mt-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i < score ? BAR_COLORS[score] : 'bg-zinc-200 dark:bg-zinc-700'
            }`}
          />
        ))}
      </div>
      <p className="text-[11px] text-zinc-500 mt-1 dark:text-zinc-400">
        {t(LABEL_KEYS[score])}
      </p>
    </div>
  );
}
