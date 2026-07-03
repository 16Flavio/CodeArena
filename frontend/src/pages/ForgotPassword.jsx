import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { forgotPassword } from '../api';
import { Zap, Mail, CheckCircle, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../utils/apiError';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword({ email });
      setSent(true);
    } catch (err) {
      toast.error(extractErrorMessage(err, t('auth.somethingWentWrong')));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-zinc-50 dark:bg-zinc-950">

      <div className="relative card p-8 w-full max-w-md animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-lg bg-accent-600 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-2xl font-bold text-zinc-900 dark:text-white">CodeArena</span>
        </div>

        {sent ? (
          <div className="text-center">
            <div className="w-14 h-14 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center mx-auto mb-5">
              <CheckCircle className="w-7 h-7 text-emerald-500 dark:text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-zinc-900 mb-3 dark:text-white">{t('auth.checkInbox')}</h2>
            <p className="text-zinc-500 mb-6 leading-relaxed dark:text-zinc-400">
              {t('auth.checkInboxBody', { email })}
            </p>
            <Link to="/login" className="btn-primary w-full inline-block text-center">
              <ArrowLeft className="w-4 h-4 mr-2 inline" />
              {t('auth.backToSignIn')}
            </Link>
          </div>
        ) : (
          <>
            <h2 className="text-2xl font-bold text-zinc-900 text-center mb-2 dark:text-white">
              {t('auth.forgotTitle')}
            </h2>
            <p className="text-zinc-500 text-center mb-8 dark:text-zinc-400">
              {t('auth.forgotSubtitle')}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2 dark:text-zinc-300">
                  {t('auth.email')}
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none dark:text-zinc-500" />
                  <input
                    type="email"
                    className="input-field pl-10"
                    placeholder="vous@exemple.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {t('auth.forgotSending')}
                  </span>
                ) : (
                  t('auth.forgotButton')
                )}
              </button>
            </form>

            <p className="text-center text-zinc-500 text-sm mt-6 dark:text-zinc-500">
              <Link to="/login" className="text-accent-600 hover:text-accent-500 font-medium dark:text-accent-400 dark:hover:text-accent-300">
                <ArrowLeft className="w-3.5 h-3.5 mr-1 inline" />
                {t('auth.backToSignIn')}
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
