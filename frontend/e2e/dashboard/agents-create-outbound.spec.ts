import { BrowserContext, expect, Page, test as base } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
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

// ── Helpers ───────────────────────────────────────────────────────────────────

async function ensureOnPage(page: Page): Promise<void> {
  if (page.url().includes('/agents/create/outbound')) return;
  await page.goto('/agents/create/outbound');
}

async function mockUpsertAPI(
  page: Page,
): Promise<Record<string, unknown>[]> {
  const captured: Record<string, unknown>[] = [];
  await page.route('**/agent/upsert_agent', async (route) => {
    const body = route.request().postDataJSON();
    captured.push(body);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 99, ...body }),
    });
  });
  return captured;
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Create Outbound Agent Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnPage(page);
  });

  // ── 1. Page Rendering ───────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows agent name in sidebar', async ({ page }) => {
      await expect(page.getByText('My Outbound Assistant')).toBeVisible();
    });

    test('shows Outbound chip in sidebar', async ({ page }) => {
      const chip = page.locator('.MuiChip-root').filter({ hasText: 'Outbound' });
      await expect(chip).toBeVisible();
    });

    test('shows info alert about making calls', async ({ page }) => {
      await expect(page.locator('.MuiAlert-root')).toContainText("can't make calls");
    });

    test('shows sidebar menu items', async ({ page }) => {
      // Outbound sidebar uses capitalized strings rendered as body2 Typography (<p>)
      await expect(page.locator('p').filter({ hasText: /^Configure$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Prompt$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Actions$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Deployment$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Calls$/ })).toBeVisible();
    });

    test('shows Configure heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Configure', level: 5 })).toBeVisible();
    });
  });

  // ── 2. General Tab Defaults ─────────────────────────────────────────────────
  test.describe('General Tab Defaults', () => {
    test('shows default outbound agent name', async ({ page }) => {
      const nameInput = page.locator('input[value="My Outbound Assistant"]');
      await expect(nameInput).toBeVisible();
    });

    test('shows default AI model', async ({ page }) => {
      await expect(page.getByText('GPT-4.1')).toBeVisible();
    });
  });

  // ── 3. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/agents/create/outbound');
    });

    test('sends outbound agent_type in payload', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        name: 'My Outbound Assistant',
        agent_type: 'outbound',
      });
    });

    test('redirects to /agents after save', async ({ page }) => {
      await mockUpsertAPI(page);
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });

    test('saves outbound agent to DB and shows in list (real API)', async ({ page }) => {
      // No mocks: triggers actual save to backend/DB. Requires running backend (NEXT_PUBLIC_BACKEND_URL).
      const agentName = 'My Outbound Assistant';

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 15_000 });

      await expect(page.getByText(agentName).first()).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText('Outbound').first()).toBeVisible();
    });
  });

  // ── 4. Back Navigation ─────────────────────────────────────────────────────
  test.describe('Back Navigation', () => {
    test('navigates to /agents when clicking Back to Agents', async ({ page }) => {
      await page.getByRole('button', { name: /back to agents/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });
  });

  // ── 5. Auth Redirect ──────────────────────────────────────────────────────
  test.describe('Auth Redirect', () => {
    let savedCookies: Awaited<ReturnType<BrowserContext['cookies']>>;

    test.beforeEach(async ({ page }) => {
      savedCookies = await page.context().cookies();
    });

    test.afterEach(async ({ page }) => {
      await page.context().addCookies(savedCookies);
    });

    test('redirects to login when no auth cookie is set', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/agents/create/outbound');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });
  });
});
