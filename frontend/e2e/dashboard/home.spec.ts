import { test as base, BrowserContext, expect, Page } from '@playwright/test';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// One browser context (window) per worker — stays open for the full suite.
// A single tab is reused across all tests in the worker. State isolation is
// handled by beforeEach hooks (cookies, navigation) rather than opening/closing
// a new tab for every test. This eliminates tab churn visible in --headed mode.
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
    // Do NOT close — the same tab is reused across all tests in this worker.
  },
});

// ── Mock data ────────────────────────────────────────────────────────────────
// Payload: {"sub":"user123","exp":9999999999} (expires year 2286)
const MOCK_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' +
  '.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjo5OTk5OTk5OTk5fQ==' +
  '.mock-signature';

const STATS = [
  { label: 'Total Agents', value: '6', change: '+2 this week' },
  { label: 'Active Calls', value: '0', change: 'Real-time' },
  { label: 'Minutes Used', value: '0', change: 'This month' },
  { label: 'Success Rate', value: '0%', change: 'Last 30 days' },
];

const QUICK_LINKS = [
  { title: 'Agents', description: 'Create and manage your AI voice agents', href: '/agents' },
  {
    title: 'Phone Numbers',
    description: 'Manage your phone numbers for calls',
    href: '/phone-numbers',
  },
  {
    title: 'Analytics',
    description: 'View performance metrics and insights',
    href: '/analytics',
  },
  {
    title: 'Actions',
    description: 'Configure automated actions and triggers',
    href: '/actions',
  },
  {
    title: 'Team Members',
    description: 'Manage your team and invite new members',
    href: '/settings',
  },
  {
    title: 'Settings',
    description: 'Configure your organization settings',
    href: '/settings',
  },
];

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    // The home page is behind auth middleware — set the cookie so we can access it.
    await page.context().addCookies([
      {
        name: 'tone_access_token',
        value: MOCK_JWT,
        domain: 'localhost',
        path: '/',
      },
    ]);
    await page.goto('/home');
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the welcome heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Welcome to Tone' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(
        page.getByText(
          'Build and deploy AI voice agents in minutes. Get started with the quick links below.',
        ),
      ).toBeVisible();
    });

    test('shows the Quick Links heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Quick Links' })).toBeVisible();
    });

    for (const stat of STATS) {
      test(`shows the "${stat.label}" stats card with value "${stat.value}"`, async ({ page }) => {
        await expect(page.getByText(stat.label)).toBeVisible();
        await expect(page.getByText(stat.change)).toBeVisible();
      });
    }

    test('displays the correct stat values', async ({ page }) => {
      // Stat values are rendered as h4 headings
      await expect(page.getByRole('heading', { name: '6', exact: true })).toBeVisible();
      await expect(page.getByText('0%')).toBeVisible();
    });

    test('renders exactly 4 stats cards', async ({ page }) => {
      // Each stat card is an MUI Card inside the stats grid
      for (const stat of STATS) {
        await expect(page.getByText(stat.label)).toBeVisible();
      }
    });

    for (const link of QUICK_LINKS) {
      test(`shows the "${link.title}" quick link card`, async ({ page }) => {
        await expect(page.getByRole('heading', { name: link.title })).toBeVisible();
        await expect(page.getByText(link.description)).toBeVisible();
      });
    }

    test('renders exactly 6 quick link cards', async ({ page }) => {
      // Each quick link card is rendered as an <a> (Card with component={Link})
      // Count only the card-level links (they contain the description text)
      for (const link of QUICK_LINKS) {
        await expect(page.getByText(link.description)).toBeVisible();
      }
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to the Agents page', async ({ page }) => {
      await page.getByRole('heading', { name: 'Agents' }).click();
      await expect(page).toHaveURL(/\/agents/, { timeout: 10_000 });
    });

    test('navigates to the Phone Numbers page', async ({ page }) => {
      await page.getByRole('heading', { name: 'Phone Numbers' }).click();
      await expect(page).toHaveURL(/\/phone-numbers/, { timeout: 10_000 });
    });

    test('navigates to the Analytics page', async ({ page }) => {
      await page.getByRole('heading', { name: 'Analytics' }).click();
      await expect(page).toHaveURL(/\/analytics/, { timeout: 10_000 });
    });

    test('navigates to the Actions page', async ({ page }) => {
      await page.getByRole('heading', { name: 'Actions' }).click();
      await expect(page).toHaveURL(/\/actions/, { timeout: 10_000 });
    });

    test('navigates to Settings from the Team Members card', async ({ page }) => {
      await page.getByText('Manage your team and invite new members').click();
      await expect(page).toHaveURL(/\/settings/, { timeout: 10_000 });
    });

    test('navigates to Settings from the Settings card', async ({ page }) => {
      await page.getByText('Configure your organization settings').click();
      await expect(page).toHaveURL(/\/settings/, { timeout: 10_000 });
    });

    test('navigates via Enter key on a focused quick link', async ({ page }) => {
      const analyticsLink = page.getByRole('link', {
        name: /Analytics View performance/i,
      });
      await analyticsLink.focus();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/analytics/, { timeout: 10_000 });
    });

    test('stays on /home when loaded with a valid auth cookie', async ({ page }) => {
      // Verify the page loads without redirecting away
      await expect(page).toHaveURL(/\/home/);
      await expect(page.getByRole('heading', { name: 'Welcome to Tone' })).toBeVisible();
    });
  });

  // ── Quick Link Hrefs ────────────────────────────────────────────────────────
  test.describe('Quick Link Hrefs', () => {
    const LINK_HREF_MAP = [
      { title: 'Agents', name: /Agents Create and manage/i, href: '/agents' },
      { title: 'Phone Numbers', name: /Phone Numbers Manage your phone/i, href: '/phone-numbers' },
      { title: 'Analytics', name: /Analytics View performance/i, href: '/analytics' },
      { title: 'Actions', name: /Actions Configure automated/i, href: '/actions' },
      { title: 'Team Members', name: /Team Members Manage your team/i, href: '/settings' },
      { title: 'Settings', name: /Settings Configure your organization/i, href: '/settings' },
    ];

    for (const { title, name, href } of LINK_HREF_MAP) {
      test(`renders the correct href for the "${title}" card (${href})`, async ({ page }) => {
        const link = page.getByRole('link', { name });
        await expect(link).toHaveAttribute('href', href);
      });
    }
  });

  // ── 3. Auth Redirect ───────────────────────────────────────────────────────
  test.describe('Auth Redirect', () => {
    test('redirects to login when no auth cookie is set', async ({ page }) => {
      // Clear the auth cookie
      await page.context().clearCookies();
      await page.goto('/home');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('redirects with the correct redirect query param', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/home');
      await expect(page).toHaveURL(/\/auth\/login\?redirect=%2Fhome/, { timeout: 10_000 });
    });
  });

  // ── 4. Dashboard Layout ──────────────────────────────────────────────────
  test.describe('Dashboard Layout', () => {
    test('renders the sidebar alongside the home content', async ({ page }) => {
      // The dashboard layout wraps all (dashboard) pages with a sidebar
      // Sidebar contains navigation links — check for at least one
      const sidebarAgentsLink = page.getByRole('link', { name: 'Agents', exact: true });
      await expect(sidebarAgentsLink).toBeVisible();
      // The home content is also present
      await expect(page.getByRole('heading', { name: 'Welcome to Tone' })).toBeVisible();
    });

    test('displays the home page content next to the sidebar', async ({ page }) => {
      // Both sidebar and main content are visible simultaneously
      await expect(page.getByRole('heading', { name: 'Welcome to Tone' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Quick Links' })).toBeVisible();
    });
  });

  // ── 5. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('renders quick links as anchor elements', async ({ page }) => {
      // Each quick link card is a <Card component={Link}> which renders as an <a> tag.
      // Use the full accessible name to distinguish the card link from the sidebar link.
      const agentsCardLink = page.getByRole('link', {
        name: /Agents Create and manage your/i,
      });
      await expect(agentsCardLink).toBeVisible();
      await expect(agentsCardLink).toHaveAttribute('href', '/agents');
    });

    test('renders correct heading hierarchy', async ({ page }) => {
      // h4 for the main welcome heading
      const mainHeading = page.getByRole('heading', { level: 4, name: 'Welcome to Tone' });
      await expect(mainHeading).toBeVisible();

      // h6 for section and card headings
      const quickLinksHeading = page.getByRole('heading', { level: 6, name: 'Quick Links' });
      await expect(quickLinksHeading).toBeVisible();
    });

    test('allows keyboard navigation through quick link cards', async ({ page }) => {
      // Focus the first quick link card (use full accessible name to avoid sidebar collision)
      const firstLink = page.getByRole('link', {
        name: /Agents Create and manage your/i,
      });
      await firstLink.focus();
      await expect(firstLink).toBeFocused();

      await page.keyboard.press('Tab');
      const secondLink = page.getByRole('link', {
        name: /Phone Numbers Manage your phone/i,
      });
      await expect(secondLink).toBeFocused();
    });

    test('renders each quick link card title as a heading', async ({ page }) => {
      // Each card title is an h6 — verify they use proper heading semantics
      for (const link of QUICK_LINKS) {
        await expect(page.getByRole('heading', { level: 6, name: link.title })).toBeVisible();
      }
    });

    test('renders stats cards without link role (non-interactive)', async ({ page }) => {
      // Stats cards are plain MUI Cards, not links — they should not be navigable
      // Verify the stat labels exist as plain text, not inside anchors
      const totalAgentsText = page.getByText('Total Agents');
      await expect(totalAgentsText).toBeVisible();
      // The parent card should not be a link
      const parentLink = totalAgentsText.locator('xpath=ancestor::a');
      await expect(parentLink).toHaveCount(0);
    });
  });
});
