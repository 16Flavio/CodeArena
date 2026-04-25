// Playwright smoke-test config. Runs a dedicated backend + frontend pair
// on non-default ports so it doesn't collide with `npm run dev`.
//
// Each run starts from an empty SQLite file (the `globalSetup` below
// deletes it), which lets tests rely on "first user becomes admin" to
// bootstrap auth without hand-maintained fixtures.
import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { rmSync, mkdirSync } from 'node:fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..');

const BACKEND_PORT = 8001;
const FRONTEND_PORT = 5174;

// Dedicated SQLite file for E2E. Wipe it synchronously at config-load
// time so it's gone *before* Playwright launches the backend webServer —
// globalSetup runs too late (webServer starts first), and on Windows the
// running uvicorn would hold a file lock that prevents the delete.
const E2E_DIR = resolve(__dirname, 'e2e');
const E2E_DB_PATH = resolve(E2E_DIR, 'e2e.db');
mkdirSync(E2E_DIR, { recursive: true });
for (const p of [E2E_DB_PATH, `${E2E_DB_PATH}-journal`, `${E2E_DB_PATH}-wal`, `${E2E_DB_PATH}-shm`]) {
  try { rmSync(p, { force: true }); } catch { /* ignore */ }
}
const DATABASE_URL = `sqlite:///${E2E_DB_PATH.replace(/\\/g, '/')}`;

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
