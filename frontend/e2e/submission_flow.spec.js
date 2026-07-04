// Contest creation + submission flow E2E. Builds on smoke.spec.js
// (which registers the bootstrap admin) by exercising the
// admin-creates-contest → user-submits → score-appears path that
// unit tests can't fully cover (it crosses 6+ HTTP routes, 3 React
// pages, the scoring queue, and the cache invalidation).
//
// Runs in the same Playwright project as smoke.spec.js so it shares
// the bootstrapped admin user. We use the API directly for setup
// (faster + less brittle than driving the form) and the UI only for
// the parts where the UI is the actual subject of the test.
import { test, expect, request } from '@playwright/test';

const ADMIN = {
  username: 'e2eadmin',
  password: 'E2E-Password-123!',
};

const PARTICIPANT = {
  username: 'e2eparticipant',
  email: 'participant@e2e.local',
  password: 'P@rt-Password-123',
};

async function loginViaApi(api, username, password) {
  const r = await api.post('/api/auth/login', { data: { username, password } });
  expect(r.ok(), `login response ${r.status()}: ${await r.text()}`).toBeTruthy();
  const { access_token } = await r.json();
  return access_token;
}

async function registerOrLogin(api, { username, email, password }) {
  // Don't depend on smoke.spec.js running first (alphabetical order
  // means contest_flow runs before smoke). Register first; if the
  // user already exists we get a 400 and proceed to login normally.
  const reg = await api.post('/api/auth/register', {
    data: { username, email, password },
  });
  if (reg.status() !== 200 && reg.status() !== 400) {
    throw new Error(`register ${reg.status()}: ${await reg.text()}`);
  }
  return loginViaApi(api, username, password);
}

async function ensureUser(api, adminToken, { username, email, password }) {
  // Idempotent: register, then force email_verified via the seeded
  // admin's privilege (no public endpoint for that - we go through a
  // direct registration that auto-verifies in test mode? actually
  // the test config doesn't auto-verify; we need to either skip
  // verification or use a backend test seam. Easier: just register +
  // login, accepting that some endpoints may require verification).
  const reg = await api.post('/api/auth/register', {
    data: { username, email, password },
  });
  // 200 first time, 400 if already exists - both fine.
  if (reg.status() !== 200 && reg.status() !== 400) {
    throw new Error(`register ${reg.status()}: ${await reg.text()}`);
  }
  // We can't easily verify email from outside the backend, so we
  // skip endpoints that require ``require_verified``. The contest
  // flow we test below uses ``get_current_user`` which is enough.
  return loginViaApi(api, username, password);
}

test('contest lifecycle: admin creates, registers, submits via API, sees score', async ({ playwright, page }) => {
  const api = await playwright.request.newContext({ baseURL: 'http://localhost:5174' });

  // 1. Auth as the bootstrapped admin. The first registered user
  //    becomes admin automatically - register-or-login keeps the
  //    test independent of smoke.spec.js running first.
  const adminToken = await registerOrLogin(api, {
    username: ADMIN.username,
    email: 'e2e@example.com',
    password: ADMIN.password,
  });
  const adminHeaders = { Authorization: `Bearer ${adminToken}` };

  // 2. Create a brand-new output contest, active, accepting solo
  //    submissions (so we don't have to set up a team).
  const now = new Date();
  const start = new Date(now.getTime() - 5 * 60_000).toISOString();
  const end = new Date(now.getTime() + 60 * 60_000).toISOString();
  const contestRes = await api.post('/api/contests', {
    headers: adminHeaders,
    data: {
      title: `E2E ${Date.now()}`,
      is_active: true,
      is_public: true,
      participation_mode: 'solo',
      start_time: start,
      end_time: end,
      // Score = the byte length of the submission. Easy to predict.
      scoring_script: 'score = len(submission_data)',
    },
  });
  expect(contestRes.ok(), `create contest: ${await contestRes.text()}`).toBeTruthy();
  const contest = await contestRes.json();

  // 3. Add an instance.
  const formData = new FormData();
  formData.append('name', 'inst-1');
  formData.append('file', new Blob([Buffer.from('input data')], { type: 'text/plain' }), 'in.txt');
  const instRes = await api.post(`/api/contests/${contest.id}/instances`, {
    headers: adminHeaders,
    multipart: {
      name: 'inst-1',
      file: { name: 'in.txt', mimeType: 'text/plain', buffer: Buffer.from('input data') },
    },
  });
  expect(instRes.ok(), `create instance: ${await instRes.text()}`).toBeTruthy();
  const instance = await instRes.json();

  // 4. The admin themselves can submit (they're a regular user too).
  //    Register them on the contest first.
  const regRes = await api.post(`/api/contests/${contest.id}/register`, {
    headers: adminHeaders, data: {},
  });
  expect(regRes.ok(), `register: ${await regRes.text()}`).toBeTruthy();

  // 5. Submit a known payload: 12 bytes → score should be 12.
  const submission = await api.post(
    `/api/contests/${contest.id}/instances/${instance.id}/submit`,
    {
      headers: adminHeaders,
      multipart: {
        file: { name: 's.txt', mimeType: 'text/plain', buffer: Buffer.from('hello world!') },
      },
    },
  );
  expect(submission.ok(), `submit: ${await submission.text()}`).toBeTruthy();
  const sub = await submission.json();

  // 6. Poll until the submission is scored (test fixture inlines the
  //    scoring, prod uses the queue - the dev server runs the prod
  //    path, so this can take a few hundred ms).
  let scored = null;
  for (let i = 0; i < 50; i += 1) {
    await new Promise((r) => setTimeout(r, 200));
    const r = await api.get(`/api/contests/submissions/${sub.id}`, { headers: adminHeaders });
    if (r.ok()) {
      const s = await r.json();
      if (s.status === 'scored') {
        scored = s;
        break;
      }
    }
  }
  expect(scored, 'submission never reached scored status').not.toBeNull();
  expect(scored.score).toBe(12);

  // 7. Open the scoreboard in the UI and verify the new contest +
  //    score appear. This catches SPA routing / data-binding bugs the
  //    API wouldn't.
  // First we need a logged-in browser context - drive the login form.
  await page.goto('/login');
  await page.locator('input[type="text"]').first().fill(ADMIN.username);
  await page.locator('input[type="password"]').first().fill(ADMIN.password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });

  await page.goto(`/scoreboard/${contest.id}`);
  // The scoreboard table or cards should render with a score of "12".
  await expect(page.locator('body')).toContainText('12', { timeout: 15_000 });

  await api.dispose();
});
