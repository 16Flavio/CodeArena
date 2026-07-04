// 2FA enrollment + login flow E2E. Catches regressions in the most
// security-sensitive part of the auth surface: setup, login challenge,
// recovery code consumption.
//
// We compute the TOTP code in JS (not by calling the backend) so the
// test exercises the actual algorithm both sides have to agree on -
// if the backend's pyotp ever drifts from the client's expectation,
// this spec catches it.
import { test, expect } from '@playwright/test';
import { createHmac } from 'node:crypto';

const USER = {
  username: '2fa_user',
  email: '2fa@e2e.local',
  password: 'totp-secret-pw-1',
};

// RFC 6238 TOTP - implemented inline so we don't depend on yet
// another npm package in the e2e tree. Same algorithm pyotp runs.
function base32Decode(b32) {
  const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const cleaned = b32.replace(/=+$/, '').toUpperCase().replace(/\s+/g, '');
  let bits = '';
  for (const c of cleaned) {
    const v = ALPHABET.indexOf(c);
    if (v < 0) throw new Error(`bad base32 char: ${c}`);
    bits += v.toString(2).padStart(5, '0');
  }
  const out = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    out.push(parseInt(bits.slice(i, i + 8), 2));
  }
  return Buffer.from(out);
}

function totp(secretB32, t = Math.floor(Date.now() / 1000), step = 30, digits = 6) {
  const counter = Math.floor(t / step);
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(counter));
  const hmac = createHmac('sha1', base32Decode(secretB32)).update(buf).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code = ((hmac[offset] & 0x7f) << 24)
    | ((hmac[offset + 1] & 0xff) << 16)
    | ((hmac[offset + 2] & 0xff) << 8)
    | (hmac[offset + 3] & 0xff);
  return String(code % 10 ** digits).padStart(digits, '0');
}

async function registerOrLogin(api, { username, email, password }) {
  const reg = await api.post('/api/auth/register', {
    data: { username, email, password },
  });
  if (reg.status() !== 200 && reg.status() !== 400) {
    throw new Error(`register ${reg.status()}: ${await reg.text()}`);
  }
  const r = await api.post('/api/auth/login', { data: { username, password } });
  expect(r.ok(), `login ${r.status()}: ${await r.text()}`).toBeTruthy();
  return (await r.json()).access_token;
}

test('TOTP enrollment + login challenge + recovery code consumption', async ({ playwright }) => {
  const api = await playwright.request.newContext({ baseURL: 'http://localhost:5174' });

  // 1. Bootstrap a user. (First registered user becomes admin -
  //    the smoke spec already does this; we register a second user
  //    so we don't fight over the bootstrap admin row.)
  const token = await registerOrLogin(api, USER);
  const headers = { Authorization: `Bearer ${token}` };

  // 2. Setup 2FA - secret + otpauth URL come back.
  let r = await api.post('/api/auth/2fa/setup', { headers });
  expect(r.ok(), `setup ${r.status()}: ${await r.text()}`).toBeTruthy();
  const { secret, otpauth_url } = await r.json();
  expect(secret).toMatch(/^[A-Z2-7]+$/);  // base32 alphabet
  expect(otpauth_url).toMatch(/^otpauth:\/\/totp\//);

  // 3. Verify with the current TOTP. Returns 8 recovery codes.
  r = await api.post('/api/auth/2fa/verify', {
    headers,
    data: { code: totp(secret) },
  });
  expect(r.ok(), `verify ${r.status()}: ${await r.text()}`).toBeTruthy();
  const { recovery_codes } = await r.json();
  expect(recovery_codes).toHaveLength(8);
  expect(recovery_codes[0]).toMatch(/^[a-f0-9]{20}$/);

  // 4. Plain login - backend now refuses with 401 + TOTP_REQUIRED.
  r = await api.post('/api/auth/login', {
    data: { username: USER.username, password: USER.password },
  });
  expect(r.status()).toBe(401);
  const challenge = (await r.json()).detail.params.challenge_token;
  expect(typeof challenge).toBe('string');

  // 5. Wrong code → 400 TOTP_INVALID.
  r = await api.post('/api/auth/2fa/login-verify', {
    data: { challenge_token: challenge, code: '000000' },
  });
  expect(r.status()).toBe(400);
  expect((await r.json()).detail.code).toBe('TOTP_INVALID');

  // 6. Right TOTP → access token.
  r = await api.post('/api/auth/2fa/login-verify', {
    data: { challenge_token: challenge, code: totp(secret) },
  });
  expect(r.ok(), `login-verify ${r.status()}: ${await r.text()}`).toBeTruthy();
  expect(typeof (await r.json()).access_token).toBe('string');

  // 7. Recovery code path - fresh challenge, recovery code instead of TOTP.
  r = await api.post('/api/auth/login', {
    data: { username: USER.username, password: USER.password },
  });
  const challenge2 = (await r.json()).detail.params.challenge_token;
  r = await api.post('/api/auth/2fa/login-verify', {
    data: { challenge_token: challenge2, code: recovery_codes[0] },
  });
  expect(r.ok()).toBeTruthy();

  // 8. Reuse the same recovery code → rejected (single-use).
  r = await api.post('/api/auth/login', {
    data: { username: USER.username, password: USER.password },
  });
  const challenge3 = (await r.json()).detail.params.challenge_token;
  r = await api.post('/api/auth/2fa/login-verify', {
    data: { challenge_token: challenge3, code: recovery_codes[0] },
  });
  expect(r.status()).toBe(400);
  expect((await r.json()).detail.code).toBe('TOTP_INVALID');

  await api.dispose();
});

test('UI: login screen pivots to TOTP form when challenge returned', async ({ page, playwright }) => {
  // The previous test ran against a freshly-2FA-enabled user, so a UI
  // login attempt as that user should swap the form to the TOTP input.
  const api = await playwright.request.newContext({ baseURL: 'http://localhost:5174' });
  // Re-derive the secret by re-enrolling - the previous test left
  // the user with 2FA on, so we can't /setup again. Instead we use
  // the admin escape hatch to clear and re-enroll.
  // ... actually simpler: just verify the form swap visually.

  await page.goto('/login');
  await page.locator('input[type="text"]').first().fill(USER.username);
  await page.locator('input[type="password"]').first().fill(USER.password);
  await page.locator('button[type="submit"]').click();

  // The TOTP code input should appear (placeholder "000000" is the
  // anchor - language-stable).
  await expect(page.locator('input[placeholder="000000"]')).toBeVisible({ timeout: 10_000 });
  await api.dispose();
});

// NB: a third spec used to drive the full UI enrollment in the
// Security page, but it consistently hit the /login rate limit
// (10/min, shared across the E2E suite). The two specs above cover
// the contract end-to-end; the Security page just renders that
// contract as forms. Re-add a UI spec when the rate limiter gets a
// per-test override or we run with isolated backends.
