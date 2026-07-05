import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bell, Megaphone, Send } from 'lucide-react';
import { getMyActivity } from '../api';
import { formatDateTime } from '../utils/datetime';

const POLL_MS = 60000;
const SEEN_KEY = 'notif-last-seen-at';

export default function NotificationsBell() {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [lastSeen, setLastSeen] = useState(() => Number(localStorage.getItem(SEEN_KEY) || 0));
  const rootRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await getMyActivity(30);
        if (!cancelled) setItems(r.data || []);
      } catch {
        /* ignore transient failures */
      }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    const onFocus = () => tick();
    window.addEventListener('focus', onFocus);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const unread = items.filter((it) => new Date(it.at).getTime() > lastSeen).length;

  const handleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      const now = Date.now();
      setLastSeen(now);
      localStorage.setItem(SEEN_KEY, String(now));
    }
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={handleOpen}
        className="relative p-2 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800"
        aria-label={t('notifications.openLabel')}
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500" aria-hidden />
        )}
      </button>
      {open && (
        <div className="fixed left-3 right-3 top-16 sm:absolute sm:left-auto sm:right-0 sm:top-12 sm:w-80 max-h-[70vh] overflow-y-auto card p-2 z-50 shadow-xl">
          <div className="px-3 py-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
            {t('notifications.title')}
          </div>
          {items.length === 0 ? (
            <p className="text-sm text-zinc-400 italic text-center py-6 dark:text-zinc-600">
              {t('notifications.empty')}
            </p>
          ) : (
            <ul className="space-y-1">
              {items.map((it, i) => (
                <li key={`${it.kind}-${it.contest_id}-${it.at}-${i}`}>
                  <Link
                    to={it.contest_id ? `/contests/${it.contest_id}` : '#'}
                    onClick={() => setOpen(false)}
                    className="flex items-start gap-2 p-2 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
                  >
                    {it.kind === 'announcement' ? (
                      <Megaphone className="w-4 h-4 mt-0.5 text-sky-600 dark:text-sky-400 flex-shrink-0" />
                    ) : (
                      <Send className="w-4 h-4 mt-0.5 text-accent-500 dark:text-accent-400 flex-shrink-0" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-800 truncate dark:text-zinc-200">{it.title}</p>
                      {it.body && (
                        <p className="text-xs text-zinc-500 truncate dark:text-zinc-400">{it.body}</p>
                      )}
                      <p className="text-[10px] text-zinc-400 mt-0.5 dark:text-zinc-500">{formatDateTime(it.at)}</p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
