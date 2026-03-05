import { test as base, BrowserContext, expect, Page } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Worker-scoped context = one browser window shared across all tests in this worker.
// Login happens ONCE during worker setup against the real backend, not before every test.
// A single tab is reused across all tests; beforeEach uses soft navigation.
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      const page = await context.newPage();
      await loginViaUI(page);
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
  },
});

// ── Soft navigation helper ────────────────────────────────────────────────────
// 1. Already on /home → skip (0ms)
// 2. On another dashboard page → click sidebar "Home" link (~200ms)
// 3. Outside dashboard → fall back to page.goto() (~400ms)
async function ensureOnPage(page: Page, targetPath: string): Promise<void> {
  if (page.url().includes(targetPath)) return;

  const sidebarLink = page.locator(`a[href="${targetPath}"]`).first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(new RegExp(targetPath.replace('/', '\\/')), { timeout: 5_000 });
    return;
  }

  await page.goto(targetPath);
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnPage(page, '/home');
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows "Welcome to Tone" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Welcome to Tone' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(page.getByText('Build and deploy AI voice agents in minutes.')).toBeVisible();
    });

    test('shows the "Create Agent" quick action link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Create Agent' })).toBeVisible();
    });

    test('shows the "Total Agents" stat card with value and change text', async ({ page }) => {
      await expect(page.getByText('Total Agents')).toBeVisible();
      await expect(page.getByText('+2 this week')).toBeVisible();
    });

    test('shows the "Active Calls" stat card with period text', async ({ page }) => {
      await expect(page.getByText('Active Calls')).toBeVisible();
      await expect(page.getByText('Real-time')).toBeVisible();
    });

    test('shows the "Minutes Used" stat card with period text', async ({ page }) => {
      await expect(page.getByText('Minutes Used')).toBeVisible();
      await expect(page.getByText('This month')).toBeVisible();
    });

    test('shows the "Success Rate" stat card with period text', async ({ page }) => {
      await expect(page.getByText('Success Rate')).toBeVisible();
      await expect(page.getByText('Last 30 days')).toBeVisible();
    });

    test('shows the "Quick Links" section heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Quick Links' })).toBeVisible();
    });

    test('shows all 6 quick link cards', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Agents' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Phone Numbers' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Analytics' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Actions' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Team Members' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
    });

    test('shows each quick link card with its description', async ({ page }) => {
      await expect(page.getByText('Create and manage your AI voice agents')).toBeVisible();
      await expect(page.getByText('Manage your phone numbers for calls')).toBeVisible();
      await expect(page.getByText('View performance metrics and insights')).toBeVisible();
      await expect(page.getByText('Configure automated actions and triggers')).toBeVisible();
      await expect(page.getByText('Manage your team and invite new members')).toBeVisible();
      await expect(page.getByText('Configure your organization settings')).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    // ── 2a. Href assertions (safe for all routes including non-existing ones) ──

    test('renders "Create Agent" link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Create Agent' })).toHaveAttribute(
        'href',
        '/agents',
      );
    });

    test('renders "Agents" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Agents' })).toHaveAttribute('href', '/agents');
    });

    test('renders "Phone Numbers" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Phone Numbers' })).toHaveAttribute(
        'href',
        '/phone-numbers',
      );
    });

    test('renders "Analytics" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Analytics' })).toHaveAttribute(
        'href',
        '/analytics',
      );
    });

    test('renders "Actions" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Actions' })).toHaveAttribute('href', '/actions');
    });

    test('renders "Team Members" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Team Members' })).toHaveAttribute(
        'href',
        '/settings',
      );
    });

    test('renders "Settings" card with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Settings' })).toHaveAttribute(
        'href',
        '/settings',
      );
    });

    // ── 2b. Click navigation (only for routes that exist in the app) ──────────

    test('clicking "Create Agent" navigates to /agents', async ({ page }) => {
      await page.getByRole('link', { name: 'Create Agent' }).click();
      await expect(page).toHaveURL(/\/agents/, { timeout: 10_000 });
    });

    test('clicking "Agents" card navigates to /agents', async ({ page }) => {
      await page.getByRole('link', { name: 'Agents' }).click();
      await expect(page).toHaveURL(/\/agents/, { timeout: 10_000 });
    });

    test('clicking "Phone Numbers" card navigates to /phone-numbers', async ({ page }) => {
      await page.getByRole('link', { name: 'Phone Numbers' }).click();
      await expect(page).toHaveURL(/\/phone-numbers/, { timeout: 10_000 });
    });

    test('clicking "Team Members" card navigates to /settings', async ({ page }) => {
      await page.getByRole('link', { name: 'Team Members' }).click();
      await expect(page).toHaveURL(/\/settings/, { timeout: 10_000 });
    });

    test('clicking "Settings" card navigates to /settings', async ({ page }) => {
      await page.getByRole('link', { name: 'Settings' }).click();
      await expect(page).toHaveURL(/\/settings/, { timeout: 10_000 });
    });
  });

  // ── 3. Auth Redirect ───────────────────────────────────────────────────────
  test.describe('Auth Redirect', () => {
    let savedCookies: Awaited<ReturnType<BrowserContext['cookies']>>;

    test.beforeEach(async ({ page }) => {
      savedCookies = await page.context().cookies();
    });

    test.afterEach(async ({ page }) => {
      // Restore auth cookies and navigate back so the outer beforeEach can
      // resume soft navigation on the next test.
      await page.context().addCookies(savedCookies);
      await page.goto('/home');
    });

    test('redirects to login when no auth cookie is set', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/home');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('redirect URL includes ?redirect=%2Fhome query param', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/home');
      await expect(page).toHaveURL(/redirect=%2Fhome/, { timeout: 10_000 });
    });

    test('stays on /home when valid auth cookies are present', async ({ page }) => {
      // Cookies are already set by loginViaUI in the worker fixture
      await page.goto('/home');
      await expect(page).toHaveURL(/\/home/, { timeout: 10_000 });
    });
  });

  // ── 4. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('renders "Welcome to Tone" as an h1 heading', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 1, name: 'Welcome to Tone' })).toBeVisible();
    });

    test('renders "Quick Links" as an h2 heading', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 2, name: 'Quick Links' })).toBeVisible();
    });

    test('stat cards have no link role (they are non-interactive)', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Total Agents' })).toHaveCount(0);
      await expect(page.getByRole('link', { name: 'Active Calls' })).toHaveCount(0);
      await expect(page.getByRole('link', { name: 'Minutes Used' })).toHaveCount(0);
      await expect(page.getByRole('link', { name: 'Success Rate' })).toHaveCount(0);
    });

    test('quick link cards are rendered as accessible links', async ({ page }) => {
      for (const name of [
        'Agents',
        'Phone Numbers',
        'Analytics',
        'Actions',
        'Team Members',
        'Settings',
      ]) {
        await expect(page.getByRole('link', { name })).toBeVisible();
      }
    });

    test('allows Tab navigation between quick link cards', async ({ page }) => {
      const agentsLink = page.getByRole('link', { name: 'Agents' });
      await agentsLink.focus();
      await expect(agentsLink).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByRole('link', { name: 'Phone Numbers' })).toBeFocused();
    });

    test('allows Enter key to activate a focused quick link card', async ({ page }) => {
      await page.getByRole('link', { name: 'Agents' }).focus();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/agents/, { timeout: 10_000 });
    });
  });
});
