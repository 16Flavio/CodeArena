import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { ShieldCheck, ShieldOff, Copy, Check, AlertTriangle } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useAuth } from '../AuthContext';
import { totpSetup, totpVerify, totpDisable, getMe } from '../api';
import { copyText } from '../utils/clipboard';
import { extractErrorMessage } from '../utils/apiError';

// 2FA setup / disable. The QR rendering is intentionally absent —
// we show the otpauth:// URL as a tap-to-open link (works on mobile)
// and the raw base32 secret for manual entry. Adding a QR library
// (qrcode.js or similar) is a future enhancement.
export default function Security() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();

  // Stage of the flow:
  //   'idle'    → show enable / disable buttons depending on user.totp_enabled
  //   'setup'   → secret + otpauth URL + code input
  //   'success' → recovery codes shown once
  //   'disable' → password + code form
  const [stage, setStage] = useState('idle');
  const [secret, setSecret] = useState('');
  const [otpauthUrl, setOtpauthUrl] = useState('');
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [disableForm, setDisableForm] = useState({ password: '', code: '' });
  const [busy, setBusy] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const refreshMe = async () => {
    try {
      const { data } = await getMe();
      setUser(data);
    } catch { /* ignore — the user can refresh manually */ }
  };

  const handleStartSetup = async () => {
    setBusy(true);
    try {
      const { data } = await totpSetup();
      setSecret(data.secret);
      setOtpauthUrl(data.otpauth_url);
      setCode('');
      setStage('setup');
    } catch (err) {
      toast.error(extractErrorMessage(err, t('common.somethingWentWrong')));
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await totpVerify({ code: code.trim() });
      setRecoveryCodes(data.recovery_codes);
      setStage('success');
      toast.success(t('auth.totp.settings.toastEnabled'));
      await refreshMe();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('common.somethingWentWrong')));
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await totpDisable(disableForm);
      toast.success(t('auth.totp.settings.toastDisabled'));
      setDisableForm({ password: '', code: '' });
      setStage('idle');
      await refreshMe();
    } catch (err) {
      toast.error(extractErrorMessage(err, t('common.somethingWentWrong')));
    } finally {
      setBusy(false);
    }
  };

  const copySecret = async () => {
    const ok = await copyText(secret);
    if (ok) {
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 animate-fade-in">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
        {t('auth.totp.settings.title')}
      </h1>

      {stage === 'idle' && user?.totp_enabled && (
        <div className="glass-card p-6 mt-4 space-y-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-emerald-500" />
            <div>
              <p className="font-semibold text-emerald-700 dark:text-emerald-300">
                {t('auth.totp.settings.statusEnabled')}
              </p>
              <p className="text-sm text-slate-500 dark:text-gray-400">
                {t('auth.totp.settings.intro')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => { setStage('disable'); setDisableForm({ password: '', code: '' }); }}
            className="text-sm text-red-600 hover:text-red-500 font-medium dark:text-red-400 inline-flex items-center gap-1.5"
          >
            <ShieldOff className="w-4 h-4" />
            {t('auth.totp.settings.disableBtn')}
          </button>
        </div>
      )}

      {stage === 'idle' && !user?.totp_enabled && (
        <div className="glass-card p-6 mt-4 space-y-4">
          <div className="flex items-center gap-3">
            <ShieldOff className="w-8 h-8 text-slate-400" />
            <div>
              <p className="font-semibold text-slate-700 dark:text-gray-200">
                {t('auth.totp.settings.statusDisabled')}
              </p>
              <p className="text-sm text-slate-500 dark:text-gray-400">
                {t('auth.totp.settings.intro')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleStartSetup}
            disabled={busy}
            className="btn-primary text-sm py-2 px-4 inline-flex items-center gap-2"
          >
            <ShieldCheck className="w-4 h-4" />
            {t('auth.totp.settings.setupBtn')}
          </button>
        </div>
      )}

      {stage === 'setup' && (
        <form onSubmit={handleVerify} className="glass-card p-6 mt-4 space-y-5">
          <p className="text-sm text-slate-600 dark:text-gray-300">
            {t('auth.totp.settings.scanQR')}
          </p>

          {/* QR rendered locally with qrcode.react — never hits a third
              party, the secret stays inside the user's browser. */}
          <div className="flex justify-center">
            <div className="bg-white p-4 rounded-xl inline-block">
              <QRCodeSVG value={otpauthUrl} size={200} level="M" includeMargin={false} />
            </div>
          </div>

          <div>
            <label className="text-xs uppercase tracking-wide text-slate-500 dark:text-gray-400">
              {t('auth.totp.settings.secretLabel')}
            </label>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-800/60 font-mono text-sm break-all tracking-wider">
                {/* Group every 4 chars for readability — Google Authenticator
                    accepts this format on manual entry. */}
                {secret.match(/.{1,4}/g)?.join(' ') || secret}
              </code>
              <button
                type="button"
                onClick={copySecret}
                className="btn-secondary text-sm py-2 px-3"
                aria-label="copy"
              >
                {copiedSecret ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-2">
              {t('auth.totp.settings.verifyHint')}
            </label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              className="input-field text-center text-2xl tracking-[0.5em] font-mono"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setStage('idle')} className="btn-secondary text-sm">
              {t('common.cancel')}
            </button>
            <button type="submit" disabled={busy || code.length !== 6} className="btn-primary text-sm">
              {t('auth.totp.settings.verifyBtn')}
            </button>
          </div>
        </form>
      )}

      {stage === 'success' && (
        <div className="glass-card p-6 mt-4 space-y-4 border border-amber-500/40 bg-amber-500/5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-amber-700 dark:text-amber-300">
                {t('auth.totp.settings.successTitle')}
              </p>
              <p className="text-sm text-amber-700/90 dark:text-amber-200/90 mt-1">
                {t('auth.totp.settings.successBody')}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {recoveryCodes.map((c) => (
              <code
                key={c}
                className="px-3 py-2 rounded bg-slate-50 dark:bg-slate-900 font-mono text-sm text-center select-all border border-slate-200 dark:border-slate-700"
              >
                {c}
              </code>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setStage('idle')}
            className="btn-primary text-sm w-full"
          >
            {t('auth.totp.settings.successAck')}
          </button>
        </div>
      )}

      {stage === 'disable' && (
        <form onSubmit={handleDisable} className="glass-card p-6 mt-4 space-y-4 border border-red-500/30">
          <h3 className="font-bold text-red-700 dark:text-red-300 flex items-center gap-2">
            <ShieldOff className="w-5 h-5" />
            {t('auth.totp.settings.disableTitle')}
          </h3>
          <p className="text-sm text-slate-600 dark:text-gray-300">
            {t('auth.totp.settings.disableSubtitle')}
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
              {t('auth.totp.settings.passwordLabel')}
            </label>
            <input
              type="password"
              autoComplete="current-password"
              className="input-field"
              value={disableForm.password}
              onChange={(e) => setDisableForm({ ...disableForm, password: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-gray-300 mb-1">
              {t('auth.totp.settings.codeLabel')}
            </label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="input-field font-mono"
              placeholder="000000"
              value={disableForm.code}
              onChange={(e) => setDisableForm({ ...disableForm, code: e.target.value })}
              required
            />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setStage('idle')} className="btn-secondary text-sm">
              {t('common.cancel')}
            </button>
            <button type="submit" disabled={busy} className="text-sm py-2 px-4 rounded-xl bg-red-500 hover:bg-red-400 text-white font-medium">
              {t('auth.totp.settings.disableConfirm')}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
