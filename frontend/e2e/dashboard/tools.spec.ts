import { expect, Page } from '@playwright/test';

import { test } from '../helpers/auth';

// ── Mock data ─────────────────────────────────────────────────────────────────
const MOCK_TOOLS = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    uuid: '11111111-1111-1111-1111-111111111111',
    name: 'check_inventory',
    description: 'Checks product inventory and returns availability.',
    tool_type: 'custom',
    url: 'https://api.example.com/inventory/{product_id}',
    method: 'GET',
    auth_type: 'api_key',
    auth_config: { header_name: 'X-API-Key', api_key: 'sk-xxxx' },
    meta_data: null,
    parameters: {
      type: 'object',
      properties: {
        product_id: { type: 'string', description: 'Product identifier' },
        location: { type: 'string', description: 'Store location' },
      },
      required: ['product_id'],
    },
    is_active: true,
    is_template: false,
    oauth_connection_id: null,
    mcp_server_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    uuid: '22222222-2222-2222-2222-222222222222',
    name: 'create_calendar_event',
    description: 'Create a Google Calendar event for a customer.',
    tool_type: 'google_calendar',
    url: null,
    method: 'POST',
    auth_type: 'none',
    auth_config: null,
    meta_data: { calendar_id: 'primary', timezone: 'UTC' },
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string', description: 'Event title' },
      },
    },
    is_active: false,
    is_template: false,
    oauth_connection_id: 'oauth-1',
    mcp_server_id: null,
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    uuid: '33333333-3333-3333-3333-333333333333',
    name: 'send_appointment_sms',
    description: 'Send an SMS appointment reminder via Twilio.',
    tool_type: 'send_sms',
    url: null,
    method: 'POST',
    auth_type: 'none',
    auth_config: { account_sid: 'AC***', auth_token: '***' },
    meta_data: { from_number: '+15551234567' },
    parameters: {},
    is_active: true,
    is_template: false,
    oauth_connection_id: null,
    mcp_server_id: null,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-15T00:00:00Z',
  },
];

const MOCK_LIST_RESPONSE = {
  items: MOCK_TOOLS,
  total: MOCK_TOOLS.length,
  page: 1,
  page_size: 20,
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

async function ensureOnToolsPage(page: Page): Promise<void> {
  if (/\/tools(?:\?|$)/.test(page.url())) return;

  const sidebarLink = page.locator('a[href="/tools"]').first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(/\/tools(?:\?|$)/, { timeout: 5_000 });
    return;
  }

  await page.goto('/tools');
}

async function mockToolList(page: Page, response: unknown = MOCK_LIST_RESPONSE): Promise<void> {
  await page.route('**/tool/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Tools List Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockToolList(page);
    await ensureOnToolsPage(page);
  });

  // ── 1. Page Rendering ────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the Tools heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Tools', level: 1 })).toBeVisible();
    });

    test('shows the descriptive subtitle', async ({ page }) => {
      await expect(
        page.getByText(
          'Define external API tools your voice agents can call during conversations.',
        ),
      ).toBeVisible();
    });

    test('shows the total count badge next to the heading', async ({ page }) => {
      await expect(page.getByText('3', { exact: true }).first()).toBeVisible({ timeout: 5_000 });
    });

    test('shows the search input', async ({ page }) => {
      await expect(page.getByPlaceholder('Search tools...')).toBeVisible();
    });

    test('shows the type filter dropdown', async ({ page }) => {
      await expect(page.locator('button[id="type-filter"]')).toBeVisible();
    });

    test('shows the status filter dropdown', async ({ page }) => {
      await expect(page.locator('button[id="status-filter"]')).toBeVisible();
    });

    test('shows the Create New Tool button in the header', async ({ page }) => {
      await expect(page.getByRole('button', { name: /create new tool/i }).first()).toBeVisible();
    });

    test('shows all tool rows from the API response', async ({ page }) => {
      await expect(page.getByText('check_inventory')).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText('create_calendar_event')).toBeVisible();
      await expect(page.getByText('send_appointment_sms')).toBeVisible();
    });

    test('shows descriptions under each tool name', async ({ page }) => {
      await expect(
        page.getByText('Checks product inventory and returns availability.'),
      ).toBeVisible();
    });
  });

  // ── 2. Table Columns ─────────────────────────────────────────────────────
  test.describe('Table Columns', () => {
    test('shows all column headers', async ({ page }) => {
      await expect(page.getByRole('columnheader', { name: 'Name' })).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.getByRole('columnheader', { name: 'Type' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Method' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Endpoint URL' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Auth' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Params' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();
    });

    test('renders Custom badge for custom tools', async ({ page }) => {
      const customRow = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await expect(customRow.getByText('Custom', { exact: true })).toBeVisible({ timeout: 5_000 });
    });

    test('renders Google Calendar badge for google_calendar tools', async ({ page }) => {
      const calRow = page.locator('tbody tr').filter({ hasText: 'create_calendar_event' });
      await expect(calRow.getByText('Google Calendar', { exact: true })).toBeVisible();
    });

    test('renders SMS badge for send_sms tools', async ({ page }) => {
      const smsRow = page.locator('tbody tr').filter({ hasText: 'send_appointment_sms' });
      await expect(smsRow.getByText('SMS', { exact: true })).toBeVisible();
    });

    test('renders HTTP method badge in uppercase', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await expect(row.getByText('GET', { exact: true })).toBeVisible({ timeout: 5_000 });
    });

    test('renders the endpoint URL for custom tools', async ({ page }) => {
      await expect(page.getByText('https://api.example.com/inventory/{product_id}')).toBeVisible();
    });

    test('renders auth type with underscore replaced by space and capitalized', async ({
      page,
    }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      // 'api_key' → 'api key' (rendered with capitalize CSS class)
      await expect(row.getByText('api key')).toBeVisible({ timeout: 5_000 });
    });

    test('renders dash for tools with no auth (auth_type=none)', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'create_calendar_event' });
      // auth_type is 'none' → renders '-'
      await expect(row.locator('text=-').first()).toBeVisible();
    });

    test('renders parameter count with singular/plural label', async ({ page }) => {
      const customRow = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await expect(customRow.getByText('2 params', { exact: true })).toBeVisible({
        timeout: 5_000,
      });

      const calRow = page.locator('tbody tr').filter({ hasText: 'create_calendar_event' });
      await expect(calRow.getByText('1 param', { exact: true })).toBeVisible();
    });

    test('renders Active status for active tools', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await expect(row.getByText('Active', { exact: true })).toBeVisible({ timeout: 5_000 });
    });

    test('renders Inactive status for inactive tools', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'create_calendar_event' });
      await expect(row.getByText('Inactive', { exact: true })).toBeVisible();
    });

    test('shows inline Edit and Delete buttons for each row', async ({ page }) => {
      const firstRow = page.locator('tbody tr').first();
      await expect(firstRow.getByRole('button', { name: 'Edit' })).toBeVisible({ timeout: 5_000 });
      await expect(firstRow.getByRole('button', { name: 'Delete' })).toBeVisible();
    });
  });

  // ── 3. Navigation ────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to /tools/create when clicking Create New Tool', async ({ page }) => {
      await page
        .getByRole('button', { name: /create new tool/i })
        .first()
        .click();
      await expect(page).toHaveURL(/\/tools\/create$/, { timeout: 10_000 });
    });

    test('navigates to edit page when clicking Edit in a row', async ({ page }) => {
      await expect(page.getByText('check_inventory')).toBeVisible({ timeout: 5_000 });
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await row.getByRole('button', { name: 'Edit' }).click();

      await expect(page).toHaveURL(/\/tools\/edit\/11111111-1111-1111-1111-111111111111/, {
        timeout: 10_000,
      });
    });

    test('navigates to edit page when clicking a row body', async ({ page }) => {
      await expect(page.getByText('check_inventory')).toBeVisible({ timeout: 5_000 });
      await page.getByText('check_inventory').click();
      await expect(page).toHaveURL(/\/tools\/edit\/11111111/, { timeout: 10_000 });
    });
  });

  // ── 4. Search ────────────────────────────────────────────────────────────
  test.describe('Search', () => {
    test('debounces the search request', async ({ page }) => {
      let capturedSearch: string | undefined;
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        const body = route.request().postDataJSON() ?? {};
        capturedSearch = body.search;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      await page.getByPlaceholder('Search tools...').fill('inventory');
      // SearchBar debounces by 400ms in the list page
      await expect.poll(() => capturedSearch, { timeout: 3_000 }).toBe('inventory');
    });

    test('clears the search via the X button', async ({ page }) => {
      const input = page.getByPlaceholder('Search tools...');
      await input.fill('xyz');
      await expect(input).toHaveValue('xyz');

      await page.getByRole('button', { name: /clear search/i }).click();
      await expect(input).toHaveValue('');
    });
  });

  // ── 5. Filters ───────────────────────────────────────────────────────────
  test.describe('Filters', () => {
    test('filters by tool type', async ({ page }) => {
      let lastFilter: string | undefined;
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        lastFilter = route.request().postDataJSON()?.tool_type;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      await page.locator('button[id="type-filter"]').click();
      await page.getByRole('option', { name: 'Custom' }).click();

      await expect.poll(() => lastFilter, { timeout: 5_000 }).toBe('custom');
    });

    test('filters by active status', async ({ page }) => {
      let lastIsActive: boolean | undefined;
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        lastIsActive = route.request().postDataJSON()?.is_active;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      await page.locator('button[id="status-filter"]').click();
      await page.getByRole('option', { name: 'Active', exact: true }).click();

      await expect.poll(() => lastIsActive, { timeout: 5_000 }).toBe(true);
    });

    test('filters by inactive status', async ({ page }) => {
      let lastIsActive: boolean | undefined;
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        lastIsActive = route.request().postDataJSON()?.is_active;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      await page.locator('button[id="status-filter"]').click();
      await page.getByRole('option', { name: 'Inactive' }).click();

      await expect.poll(() => lastIsActive, { timeout: 5_000 }).toBe(false);
    });

    test('lists all tool types in the type filter dropdown', async ({ page }) => {
      await page.locator('button[id="type-filter"]').click();
      await expect(page.getByRole('option', { name: 'All types' })).toBeVisible();
      await expect(page.getByRole('option', { name: 'Custom' })).toBeVisible();
      await expect(page.getByRole('option', { name: 'Send SMS' })).toBeVisible();
      await expect(page.getByRole('option', { name: 'Google Calendar' })).toBeVisible();
      await expect(page.getByRole('option', { name: 'Google Sheets' })).toBeVisible();
      await page.keyboard.press('Escape');
    });
  });

  // ── 6. Sorting ───────────────────────────────────────────────────────────
  test.describe('Sorting', () => {
    test('sends the correct sort_by parameter when clicking the Name header', async ({ page }) => {
      const sortValues: string[] = [];
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        const sort = route.request().postDataJSON()?.sort_by;
        if (sort) sortValues.push(sort);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      // initial sort is -updated_at (desc)
      await expect.poll(() => sortValues, { timeout: 5_000 }).toContain('-updated_at');

      await page.getByRole('columnheader', { name: 'Name' }).click();
      await expect
        .poll(() => sortValues[sortValues.length - 1], { timeout: 5_000 })
        .toMatch(/^-?name$/);
    });

    test('sorts by Status header', async ({ page }) => {
      const sortValues: string[] = [];
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        const sort = route.request().postDataJSON()?.sort_by;
        if (sort) sortValues.push(sort);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LIST_RESPONSE),
        });
      });

      await page.goto('/tools');
      await page.getByRole('columnheader', { name: 'Status' }).click();
      await expect
        .poll(() => sortValues[sortValues.length - 1], { timeout: 5_000 })
        .toMatch(/^-?is_active$/);
    });
  });

  // ── 7. Pagination ────────────────────────────────────────────────────────
  test.describe('Pagination', () => {
    test('sends page_size when changing the rows-per-page selector', async ({ page }) => {
      const pageSizes: number[] = [];
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await page.route('**/tool/list', async (route) => {
        const ps = route.request().postDataJSON()?.page_size;
        if (ps !== undefined) pageSizes.push(ps);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...MOCK_LIST_RESPONSE, total: 60 }),
        });
      });

      await page.goto('/tools');
      // CustomTable footer renders "Rows per page" + a native <select> with 10/20/50
      await expect(page.getByText('Rows per page')).toBeVisible({ timeout: 5_000 });
      await page.locator('select').selectOption('50');

      await expect.poll(() => pageSizes, { timeout: 5_000 }).toContain(50);
    });
  });

  // ── 8. Row Selection & Bulk Delete ───────────────────────────────────────
  test.describe('Row Selection & Bulk Delete', () => {
    // Re-mount the page between tests to reset React selection state — the tab
    // is reused so selectedIds persists otherwise.
    test.beforeEach(async ({ page }) => {
      await page.goto('/tools');
    });

    test('shows the select-all checkbox in the header', async ({ page }) => {
      await expect(page.getByRole('checkbox', { name: 'Select all' })).toBeVisible({
        timeout: 5_000,
      });
    });

    test('selects a single row and shows the selection bar with count', async ({ page }) => {
      await page.getByRole('checkbox', { name: /Select check_inventory/i }).click();
      await expect(page.getByText('tool selected', { exact: true })).toBeVisible({
        timeout: 3_000,
      });
    });

    test('selects all rows and shows plural label "tools selected"', async ({ page }) => {
      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await expect(page.getByText('tools selected', { exact: true })).toBeVisible({
        timeout: 3_000,
      });
    });

    test('clears selection via the Clear button in the selection bar', async ({ page }) => {
      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await expect(page.getByText('tools selected', { exact: true })).toBeVisible();

      const clearBtn = page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Clear', exact: true });
      await clearBtn.click();
      // SelectionBar fades out via opacity-0 + pointer-events-none — Clear becomes hit-test-blocked
      await expect(clearBtn).not.toBeVisible({ timeout: 3_000 });
    });

    test('opens the bulk-delete confirmation modal', async ({ page }) => {
      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();

      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Delete tools' })).toBeVisible();
      await expect(
        page.getByText('Delete 3 selected tools? This action cannot be undone.'),
      ).toBeVisible();
    });

    test('shows singular dialog text when only one row is selected', async ({ page }) => {
      await page.getByRole('checkbox', { name: /Select check_inventory/i }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();

      await expect(
        page.getByText('Delete 1 selected tool? This action cannot be undone.'),
      ).toBeVisible();
    });

    test('shows success toast "Tool deleted" after bulk-deleting one tool', async ({ page }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Tool deleted successfully' }),
        });
      });

      await page.getByRole('checkbox', { name: /Select check_inventory/i }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool deleted');
    });

    test('shows success toast "3 tools deleted" after bulk-deleting multiple tools', async ({
      page,
    }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });

      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

      await expect(page.locator('[data-sonner-toast]', { hasText: '3 tools deleted' })).toBeVisible(
        {
          timeout: 5_000,
        },
      );
    });

    test('shows error toast when all bulk deletes fail', async ({ page }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal error' }),
        });
      });

      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Bulk delete failed' }),
      ).toBeVisible({ timeout: 5_000 });
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'No tools were deleted.' }),
      ).toBeVisible();
    });

    test('shows partial-delete toast when some deletes fail', async ({ page }) => {
      let callCount = 0;
      await page.route('**/tool/delete_tool**', async (route) => {
        callCount += 1;
        if (callCount === 1) {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Server error' }),
          });
        } else {
          await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
        }
      });

      await page.getByRole('checkbox', { name: 'Select all' }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

      await expect(page.locator('[data-sonner-toast]', { hasText: 'Partial delete' })).toBeVisible({
        timeout: 5_000,
      });
      await expect(
        page.locator('[data-sonner-toast]', {
          hasText: /\d+ of \d+ deleted\. \d+ failed — refresh and try again\./,
        }),
      ).toBeVisible();
    });

    test('closes the bulk-delete dialog when clicking Cancel', async ({ page }) => {
      await page.getByRole('checkbox', { name: /Select check_inventory/i }).click();
      await page
        .locator('div.pointer-events-auto')
        .filter({ hasText: /selected/ })
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();

      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });

  // ── 9. Single Delete (from action menu) ──────────────────────────────────
  test.describe('Single Delete', () => {
    // Reload between tests — the modal from a prior test stays open otherwise.
    test.beforeEach(async ({ page }) => {
      await page.goto('/tools');
    });

    test('opens the per-row delete confirmation modal', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await row.getByRole('button', { name: 'Delete' }).click();

      // Per-row Delete uses ActionMenu which renders its own modal first.
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByRole('heading', { name: /delete check_inventory/i })).toBeVisible();
      await expect(
        page.getByText(
          'Are you sure you want to delete "check_inventory"? This action cannot be undone.',
        ),
      ).toBeVisible();
    });

    test('shows success toast after single delete', async ({ page }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Tool deleted successfully' }),
        });
      });

      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await row.getByRole('button', { name: 'Delete' }).click();
      // Confirm ActionMenu's modal (the only one rendered for per-row delete).
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();
      // ToolsListPage also opens its own deleteTarget modal — confirm it too.
      const listDialog = page.getByRole('dialog').filter({ hasText: 'Delete tool' });
      if (await listDialog.isVisible().catch(() => false)) {
        await listDialog.getByRole('button', { name: 'Delete' }).click();
      }

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool deleted successfully');
    });

    test('shows backend error detail in toast when single delete fails (e.g. template tool)', async ({
      page,
    }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Template tools cannot be deleted' }),
        });
      });

      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await row.getByRole('button', { name: 'Delete' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();
      const listDialog = page.getByRole('dialog').filter({ hasText: 'Delete tool' });
      if (await listDialog.isVisible().catch(() => false)) {
        await listDialog.getByRole('button', { name: 'Delete' }).click();
      }

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Template tools cannot be deleted' }),
      ).toBeVisible({ timeout: 5_000 });
    });

    test('closes the delete dialog when clicking Cancel without deleting', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: 'check_inventory' });
      await row.getByRole('button', { name: 'Delete' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();

      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });

  // ── 10. Empty State ──────────────────────────────────────────────────────
  test.describe('Empty State', () => {
    test('shows "No tools yet" empty state when list is empty', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockToolList(page, { items: [], total: 0, page: 1, page_size: 20 });
      await page.goto('/tools');

      await expect(page.getByText('No tools yet')).toBeVisible({ timeout: 5_000 });
      await expect(
        page.getByText(
          'Create your first tool to give your agents the ability to call external APIs.',
        ),
      ).toBeVisible();
    });

    test('shows "No tools match your filters" when empty list is filtered', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockToolList(page, { items: [], total: 0, page: 1, page_size: 20 });
      await page.goto('/tools');

      // apply search → empty state text changes
      await page.getByPlaceholder('Search tools...').fill('no_such_tool');
      await expect(page.getByText('No tools match your filters')).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText('Try clearing the search or filters.')).toBeVisible();
    });

    test('shows the Create New Tool button inside the empty state (no filter)', async ({
      page,
    }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockToolList(page, { items: [], total: 0, page: 1, page_size: 20 });
      await page.goto('/tools');

      // Two buttons exist: header + empty state — both labeled the same
      await expect(page.getByRole('button', { name: /create new tool/i })).toHaveCount(2, {
        timeout: 5_000,
      });
    });
  });

  // ── 11. Loading State ────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows skeleton rows while the list request is in flight', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      let resolveRoute: () => void = () => {};
      await page.route('**/tool/list', async (route) => {
        await new Promise<void>((resolve) => {
          resolveRoute = resolve;
        });
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }),
        });
      });

      await page.goto('/tools');
      await expect(page.locator('[class*="animate-pulse"]').first()).toBeVisible({
        timeout: 2_000,
      });

      resolveRoute();
    });
  });

  // ── 12. Error State ──────────────────────────────────────────────────────
  test.describe('Error State', () => {
    test('shows empty state when the list API returns 500', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await page.route('**/tool/list', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });
      await page.goto('/tools');

      await expect(page.getByText('No tools yet')).toBeVisible({ timeout: 5_000 });
    });
  });

  // ── 13. Accessibility ────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('renders page title as h1', async ({ page }) => {
      const heading = page.getByRole('heading', { name: 'Tools', level: 1 });
      await expect(heading).toBeVisible();
    });

    test('allows Create New Tool button to be activated via keyboard', async ({ page }) => {
      const btn = page.getByRole('button', { name: /create new tool/i }).first();
      await btn.focus();
      await expect(btn).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/tools\/create$/, { timeout: 10_000 });
    });

    test('checkboxes are reachable via keyboard', async ({ page }) => {
      const selectAll = page.getByRole('checkbox', { name: 'Select all' });
      await selectAll.focus();
      await page.keyboard.press('Space');
      await expect(page.getByText('tools selected', { exact: true })).toBeVisible({
        timeout: 3_000,
      });
    });
  });
});
