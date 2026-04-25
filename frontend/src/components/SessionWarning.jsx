import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle } from 'lucide-react';
import { getJwtExpMs } from '../utils/jwt';
import { getToken } from '../utils/tokenStore';

const WARN_WINDOW_MS = 10 * 60 * 1000; // 10 minutes before expiry

export default function SessionWarning() {
  const { t } = useTranslation();
  const [shouldWarn, setShouldWarn] = useState(false);

  useEffect(() => {
    const check = () => {
      const token = getToken();
      const exp = getJwtExpMs(token);
      if (!exp) {
        setShouldWarn(false);
        return;
      }
      const remaining = exp - Date.now();
      setShouldWarn(remaining > 0 && remaining < WARN_WINDOW_MS);
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  if (!shouldWarn) return null;
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-center gap-2">
      <AlertCircle className="w-4 h-4" />
      {t('auth.sessionExpiringSoon')}
    </div>
  );
}
