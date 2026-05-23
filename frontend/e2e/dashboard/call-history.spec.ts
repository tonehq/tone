import { test as base, BrowserContext, expect, Page } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

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

test.describe('Call History Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnPage(page, '/call-history');
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows "Call History" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Call History' })).toBeVisible();
    });

    test('shows date filter inputs', async ({ page }) => {
      await expect(page.getByPlaceholder('Start date')).toBeVisible();
      await expect(page.getByPlaceholder('End date')).toBeVisible();
    });

    test('shows "Apply Date Filter" button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Apply Date Filter' })).toBeVisible();
    });

    test('shows Filter and Sort buttons', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Filter', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Sort' })).toBeVisible();
    });

    test('shows the data table', async ({ page }) => {
      await expect(page.locator('table')).toBeVisible();
    });
  });

  // ── 2. Filter Modal ──────────────────────────────────────────────────────
  test.describe('Filter Modal', () => {
    test.afterEach(async ({ page }) => {
      // Close any open dialog to prevent state leakage
      if (
        await page
          .getByRole('dialog')
          .isVisible()
          .catch(() => false)
      ) {
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).not.toBeVisible();
      }
    });

    test('opens modal when clicking Filter', async ({ page }) => {
      await page.getByRole('button', { name: 'Filter', exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText('Filters').first()).toBeVisible();
    });

    test('modal contains filter field inputs', async ({ page }) => {
      await page.getByRole('button', { name: 'Filter', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();

      // Filter section heading
      await expect(dialog.getByText('Filters').first()).toBeVisible();
    });

    test('can add a new filter row', async ({ page }) => {
      await page.getByRole('button', { name: 'Filter', exact: true }).click();
      const dialog = page.getByRole('dialog');

      await dialog.getByRole('button', { name: 'Add Filter' }).click();

      // Should now have 2 filter rows by counting field select triggers
      const fieldTriggers = dialog.locator('[id^="filter-field-"]');
      await expect(fieldTriggers).toHaveCount(2);
    });

    test('modal closes when clicking Cancel', async ({ page }) => {
      await page.getByRole('button', { name: 'Filter', exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.getByRole('button', { name: 'Cancel' }).click();
      await expect(page.getByRole('dialog')).toBeHidden();
    });

    test('modal closes when clicking Apply', async ({ page }) => {
      await page.getByRole('button', { name: 'Filter', exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.getByRole('button', { name: 'Apply' }).click();
      await expect(page.getByRole('dialog')).toBeHidden();
    });
  });

  // ── 3. Sort Modal ────────────────────────────────────────────────────────
  test.describe('Sort Modal', () => {
    test.afterEach(async ({ page }) => {
      if (
        await page
          .getByRole('dialog')
          .isVisible()
          .catch(() => false)
      ) {
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).not.toBeVisible();
      }
    });

    test('opens modal when clicking Sort', async ({ page }) => {
      await page.getByRole('button', { name: 'Sort' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText('Sort').first()).toBeVisible();
    });

    test('modal closes when clicking Cancel', async ({ page }) => {
      await page.getByRole('button', { name: 'Sort' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.getByRole('button', { name: 'Cancel' }).click();
      await expect(page.getByRole('dialog')).toBeHidden();
    });

    test('modal closes when clicking Apply', async ({ page }) => {
      await page.getByRole('button', { name: 'Sort' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.getByRole('button', { name: 'Apply' }).click();
      await expect(page.getByRole('dialog')).toBeHidden();
    });
  });

  // ── 4. Sidebar Navigation ─────────────────────────────────────────────────
  test.describe('Sidebar Navigation', () => {
    test('sidebar has "Call History" link', async ({ page }) => {
      await expect(page.locator('a[href="/call-history"]')).toBeVisible();
    });

    test('clicking sidebar "Call History" navigates to /call-history', async ({ page }) => {
      await page.goto('/home');
      await page.locator('a[href="/call-history"]').click();
      await expect(page).toHaveURL(/\/call-history/, { timeout: 10_000 });
    });
  });
});
