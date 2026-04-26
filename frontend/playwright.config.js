// Playwright smoke-test config. Runs a dedicated backend + frontend pair
// on non-default ports so it doesn't collide with `npm run dev`.
//
// Each run starts from an empty SQLite file (deleted at config-load
// time below), which lets tests rely on "first user becomes admin"
// to bootstrap auth without hand-maintained fixtures.
import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';
import { mkdtempSync, chmodSync, writeFileSync, accessSync, constants } from 'node:fs';
import { tmpdir } from 'node:os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');

const BACKEND_PORT = 8001;
const FRONTEND_PORT = 5174;

// Dedicated SQLite file for E2E. ``mkdtempSync`` creates a UNIQUE
// directory under the OS temp folder for each playwright invocation,
// so there is zero chance of a stale journal/WAL from a previous run
// being picked up. The directory is owned by the runner user (chmod
// 0700 by default) and we additionally chmod 0755 below to be sure
// SQLite can create + lock journal files.
const E2E_DIR = mkdtempSync(join(tmpdir(), 'codearena-e2e-'));
chmodSync(E2E_DIR, 0o755);
const E2E_DB_PATH = join(E2E_DIR, 'e2e.db');

// Sanity: the dir IS writable. Catches the (theoretical) case where
// `mkdtempSync` succeeded but the runner umask stripped write
// permission. Crash early with a clear message if so.
try {
  writeFileSync(join(E2E_DIR, '.writable-probe'), 'ok');
  accessSync(E2E_DIR, constants.W_OK);
} catch (err) {
  throw new Error(
    `E2E temp dir ${E2E_DIR} is not writable (${err.message}). ` +
    `Investigate runner perms / umask.`,
  );
}

const DATABASE_URL = `sqlite:///${E2E_DB_PATH.replace(/\\/g, '/')}`;
// Echo what we resolved to so the GitHub Actions log makes the
// next failure (if any) easy to triage.
process.stdout.write(
  `[playwright config] E2E_DIR=${E2E_DIR}\n` +
  `[playwright config] DATABASE_URL=${DATABASE_URL}\n`,
);

export default defineConfig({
  testDir: './e2e',
  // One worker — the backend DB is shared between tests in the same run.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: `python -m uvicorn backend.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: repoRoot,
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 60_000,
      env: {
        DATABASE_URL,
        // Don't send real email during registration.
        SMTP_HOST: '',
        SMTP_PORT: '',
        SMTP_USER: '',
        SMTP_PASSWORD: '',
        // Never touch Docker from the E2E backend.
        SCORING_MODE: 'subprocess',
        SECRET_KEY: 'e2e-insecure-secret',
        // Force the worker into its in-process thread-pool fallback so we
        // don't depend on Redis/RQ for smoke tests.
        REDIS_URL: '',
      },
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: __dirname,
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 60_000,
      env: {
        VITE_API_TARGET: `http://127.0.0.1:${BACKEND_PORT}`,
      },
    },
  ],
});
