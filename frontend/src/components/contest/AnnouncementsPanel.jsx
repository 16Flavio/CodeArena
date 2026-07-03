import { useState, useEffect } from 'react';
import { Megaphone, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { listAnnouncements, createAnnouncement, deleteAnnouncement } from '../../api';
import { useConfirm } from '../Confirm';
import { formatDateTime } from '../../utils/datetime';
import { extractErrorMessage } from '../../utils/apiError';

// Announcement feed plus the admin-only publish form. Owns its own
// fetch/refresh cycle; renders nothing for non-admins when the feed
// is empty.
export default function AnnouncementsPanel({ contestId, isAdmin }) {
  const { t } = useTranslation();
  const confirm = useConfirm();
  const [announcements, setAnnouncements] = useState([]);
  const [annForm, setAnnForm] = useState({ title: '', body: '' });
  const [annSubmitting, setAnnSubmitting] = useState(false);

  useEffect(() => {
    listAnnouncements(contestId)
      .then((r) => setAnnouncements(r.data))
      .catch(() => {});
  }, [contestId]);

  const refreshAnnouncements = async () => {
    try {
      const r = await listAnnouncements(contestId);
      setAnnouncements(r.data);
    } catch {
      /* ignore */
    }
  };

  const handleCreateAnnouncement = async (e) => {
    e.preventDefault();
    if (!annForm.body.trim()) return;
    setAnnSubmitting(true);
    try {
      await createAnnouncement(contestId, annForm);
      toast.success(t('contest.toastAnnouncePublished'));
      setAnnForm({ title: '', body: '' });
      refreshAnnouncements();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('contest.toastAnnounceFailed')));
    } finally {
      setAnnSubmitting(false);
    }
  };

  const handleDeleteAnnouncement = async (id) => {
    const ok = await confirm({
      message: t('contest.confirmDeleteAnn'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteAnnouncement(id);
      refreshAnnouncements();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('admin.users.toastFailed')));
    }
  };

  if (announcements.length === 0 && !isAdmin) return null;

  return (
    <div className="glass-card p-5 border border-sky-500/30 bg-sky-500/5">
      <h2 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2 dark:text-white">
        <Megaphone className="w-5 h-5 text-sky-600 dark:text-sky-400" />
        {t('contest.announcements')}
      </h2>
      {isAdmin && (
        <form onSubmit={handleCreateAnnouncement} className="space-y-2 mb-4 p-3 rounded-xl bg-white/70 border border-sky-500/20 dark:bg-slate-900/50">
          <input
            type="text"
            className="input-field text-sm py-2"
            placeholder={t('contest.annTitleOptional')}
            value={annForm.title}
            onChange={(e) => setAnnForm({ ...annForm, title: e.target.value })}
            maxLength={200}
          />
          <textarea
            className="input-field text-sm py-2 min-h-[80px]"
            placeholder={t('contest.annBodyPlaceholder')}
            value={annForm.body}
            onChange={(e) => setAnnForm({ ...annForm, body: e.target.value })}
            required
          />
          <div className="flex justify-end">
            <button
              type="submit"
              className="btn-primary text-sm py-1.5 px-4"
              disabled={annSubmitting || !annForm.body.trim()}
            >
              {annSubmitting ? t('contest.publishing') : t('contest.publish')}
            </button>
          </div>
        </form>
      )}
      {announcements.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-gray-400">{t('contest.noAnnouncements')}</p>
      ) : (
        <div className="space-y-3">
          {announcements.map((a) => (
            <div key={a.id} className="rounded-xl p-3 bg-white/70 border border-sky-500/20 flex items-start justify-between gap-3 dark:bg-slate-900/50">
              <div className="min-w-0 flex-1">
                {a.title && (
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">{a.title}</p>
                )}
                <p className="text-sm text-slate-700 whitespace-pre-wrap mt-1 dark:text-gray-200">{a.body}</p>
                <p className="text-[11px] text-slate-500 mt-2 dark:text-gray-500">
                  {a.author_username ? `${a.author_username} · ` : ''}
                  {formatDateTime(a.created_at)}
                </p>{/* */}
              </div>
              {isAdmin && (
                <button
                  onClick={() => handleDeleteAnnouncement(a.id)}
                  className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors flex-shrink-0 dark:text-gray-500 dark:hover:text-red-400"
                  title={t('common.delete')}
                >
                  <XCircle className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
