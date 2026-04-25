// Smoke tests: prove the register → login → dashboard → admin flow
// still works after every UI refactor. They don't exercise business
// logic — the backend pytest suite does that — but catch the class of
// regressions backend tests can't see (routing, auth context wiring,
// translation keys, lazy-loaded chunks failing to mount).
//
// Tests share one worker + one DB; order matters. The first test
// registers the only user, which becomes the auto-admin. Later tests
// reuse that user by logging in again.
import { test, expect } from '@playwright/test';

const ADMIN = {
  username: 'e2eadmin',
  email: 'e2e@example.com',
  password: 'E2E-Password-123!',
};

async function login(page) {
  await page.goto('/login');
  await page.locator('input[type="text"]').first().fill(ADMIN.username);
  await page.locator('input[type="password"]').first().fill(ADMIN.password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
}

test('landing page renders', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('body')).toContainText(/CodeArena/i);
});

test('register → first user becomes admin → dashboard loads', async ({ page }) => {
  await page.goto('/register');
  await page.locator('input[type="text"]').first().fill(ADMIN.username);
  await page.locator('input[type="email"]').first().fill(ADMIN.email);
  // The register form has two type=password inputs (password + confirm).
  const pw = page.locator('input[type="password"]');
  await pw.nth(0).fill(ADMIN.password);
  await pw.nth(1).fill(ADMIN.password);
  await page.locator('button[type="submit"]').click();

  // Register auto-logs in on success.
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
  await expect(page.locator('body')).toContainText(ADMIN.username);
});

test('login → dashboard shows username + admin link', async ({ page }) => {
  await login(page);
  await expect(page.locator('body')).toContainText(ADMIN.username);
  // Admin-only nav entry must be visible for the bootstrapped admin.
  await expect(page.locator('a[href="/admin"]').first()).toBeVisible();
});

test('admin panel is reachable and renders without bouncing to /login', async ({ page }) => {
  await login(page);
  await page.goto('/admin');
  await expect(page).toHaveURL(/\/admin/);
  // Lazy-loaded chunk must mount — we assert *any* admin-ish content is
  // rendered, not the RouteSpinner fallback alone.
  await expect(page.locator('body')).toContainText(/admin|utilisateur|user/i, {
    timeout: 15_000,
  });
});
