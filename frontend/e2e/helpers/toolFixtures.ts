/**
 * Real-backend fixtures for the tools e2e specs.
 *
 * Mirrors the shape of `agentFixtures.ts`: drives the real UI, names every
 * fixture with the `__e2e__` prefix so a sweep can find orphans from aborted
 * runs, and exposes one helper per writable form field.
 *
 * Why no API client: the app's Axios instance injects auth + tenant headers
 * from cookies, so re-implementing it here would drift over time.
 */

import { expect, type Page } from '@playwright/test';

import { pickFirstSelectOption } from './agentFixtures';

export const E2E_TOOL_PREFIX = '__e2e__';

export function uniqueToolName(label: string): string {
  // Function names must be a valid identifier — collapse non-word chars to `_`.
  const safe = label.replace(/[^a-zA-Z0-9]+/g, '_');
  return `${E2E_TOOL_PREFIX}${safe}_${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
}

// ── Form navigation ─────────────────────────────────────────────────────────

/** Navigate to the custom-tool create form. */
export async function gotoCreateCustom(page: Page): Promise<void> {
  await page.goto('/tools/create/custom');
  await page.locator('input[name="name"]').first().waitFor({ state: 'visible', timeout: 15_000 });
}

/** Open the type-picker page. */
export async function gotoCreatePicker(page: Page): Promise<void> {
  await page.goto('/tools/create');
  await expect(page.getByText('Custom Tool').first()).toBeVisible({ timeout: 15_000 });
}

export async function openEditTool(page: Page, options: { id: string }): Promise<void> {
  await page.goto(`/tools/edit/${options.id}`);
  await page.locator('input[name="name"]').first().waitFor({ state: 'visible', timeout: 15_000 });
}

// ── SelectInput pickers (shadcn) ────────────────────────────────────────────

/** Pick a specific option by visible label from a SelectInput trigger. */
export async function pickSelectOptionByLabel(
  page: Page,
  trigger: ReturnType<Page['locator']>,
  label: string,
): Promise<boolean> {
  await trigger.click();
  const listbox = page.getByRole('listbox').first();
  const option = listbox.getByRole('option', { name: label, exact: true }).first();
  if (!(await option.isVisible({ timeout: 3_000 }).catch(() => false))) {
    await page.keyboard.press('Escape').catch(() => undefined);
    return false;
  }
  await option.click();
  return true;
}

export async function setHttpMethod(page: Page, method: string): Promise<boolean> {
  const trigger = page.locator('button[name="tool-method"]').first();
  return pickSelectOptionByLabel(page, trigger, method);
}

export async function setAuthType(
  page: Page,
  type: 'none' | 'api_key' | 'bearer' | 'basic',
): Promise<boolean> {
  const labelMap: Record<typeof type, string> = {
    none: 'No Authentication',
    api_key: 'API Key',
    bearer: 'Bearer Token',
    basic: 'Basic Auth',
  };
  const trigger = page.locator('button[name="tool-auth-type"]').first();
  return pickSelectOptionByLabel(page, trigger, labelMap[type]);
}

// ── Parameter builder ───────────────────────────────────────────────────────

export interface ParameterInput {
  name: string;
  type?: 'string' | 'number' | 'integer' | 'boolean' | 'array';
  description?: string;
  required?: boolean;
}

/**
 * Click "Add parameter", then fill the row that was just appended (resolved
 * via the last `input[name^="param-name-"]`).
 */
export async function addParameter(page: Page, p: ParameterInput): Promise<boolean> {
  await page
    .getByRole('button', { name: /add parameter/i })
    .first()
    .click();
  const nameInputs = page.locator('input[name^="param-name-"]');
  const lastIndex = (await nameInputs.count()) - 1;
  if (lastIndex < 0) return false;
  const lastName = nameInputs.nth(lastIndex);
  await lastName.fill(p.name);

  // Resolve the row id from the freshly-added input so we can target its
  // sibling controls. The id is everything after `param-name-`.
  const fullName = (await lastName.getAttribute('name')) ?? '';
  const rowId = fullName.replace(/^param-name-/, '');
  if (!rowId) return false;

  if (p.type) {
    const typeTrigger = page.locator(`button[name="param-type-${rowId}"]`).first();
    await pickSelectOptionByLabel(page, typeTrigger, p.type);
  }
  if (p.description !== undefined) {
    await page.locator(`input[name="param-desc-${rowId}"]`).fill(p.description);
  }
  if (p.required) {
    await page.locator(`#param-req-${rowId}`).click();
  }
  return true;
}

/** Remove every parameter row by clicking each row's Trash button. */
export async function removeAllParameters(page: Page): Promise<number> {
  const removeButtons = page.getByRole('button', { name: /remove parameter/i });
  let removed = 0;
  // The list shrinks as we click, so re-resolve `first()` every iteration.
  while (
    await removeButtons
      .first()
      .isVisible({ timeout: 500 })
      .catch(() => false)
  ) {
    await removeButtons.first().click();
    removed += 1;
    if (removed > 50) break; // safety bound; no tool should have 50+ params
  }
  return removed;
}

// ── Tool creation + cleanup ─────────────────────────────────────────────────

export interface CreateCustomToolValues {
  name?: string;
  description?: string;
  url?: string;
  method?: string;
}

/**
 * Create a custom tool through the UI, returning the id we resolve by
 * visiting `/tools` and reading the edit-route URL the row click yields.
 */
export async function createCustomToolViaUI(
  page: Page,
  values: CreateCustomToolValues = {},
): Promise<{ id: string; name: string }> {
  const name = values.name ?? uniqueToolName('tool');
  const description = values.description ?? 'E2E custom tool fixture.';
  const url = values.url ?? 'https://api.example.com/e2e';
  const method = values.method ?? 'POST';

  await gotoCreateCustom(page);
  await page.locator('input[name="name"]').first().fill(name);
  await page.locator('textarea[name="description"]').first().fill(description);
  await page.locator('input[name="url"]').first().fill(url);
  if (method !== 'POST') {
    await setHttpMethod(page, method);
  }

  await page.getByRole('button', { name: /^create$/i }).click();
  await page.waitForURL(/\/tools(?:\?|$|\/)/, { timeout: 20_000 });
  // The success toast is async; resolve it before going to the list so the
  // new row is queryable.
  await expect(page.locator('[data-sonner-toast]').first()).toContainText(
    /tool created successfully/i,
    { timeout: 10_000 },
  );

  // Read the id back from the list. CustomTable rows fire router.push to
  // `/tools/edit/{id}` on click — clicking the row by its unique name and
  // grabbing the URL is the cleanest way to learn the id.
  await page.goto('/tools');
  const row = page.locator('tbody tr').filter({ hasText: name }).first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();
  await page.waitForURL(/\/tools\/edit\/[\w-]+/, { timeout: 10_000 });
  const match = page.url().match(/\/tools\/edit\/([\w-]+)/);
  if (!match) throw new Error(`Could not parse tool id from URL: ${page.url()}`);
  return { id: match[1], name };
}

/**
 * Best-effort delete via the UI. Custom tools have no Delete button on the
 * edit page (only built-in tools do via the kebab menu), so we use the
 * per-row Delete icon on the `/tools` list page. The tool name is the
 * stable handle. Swallows errors so a teardown failure never fails a test
 * that already passed.
 */
export async function deleteToolViaUI(
  page: Page,
  options: { id?: string; name?: string },
): Promise<void> {
  try {
    await page.goto('/tools');
    await page.waitForLoadState('networkidle', { timeout: 10_000 });
    const handle = options.name ?? options.id;
    if (!handle) return;
    const row = page.locator('tbody tr').filter({ hasText: handle }).first();
    if (!(await row.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await row.getByRole('button', { name: 'Delete', exact: true }).click({ force: true });
    await page.getByRole('dialog').getByRole('button', { name: 'Delete', exact: true }).click();
    // Confirmation toast / row removal — wait for the row to be gone.
    await expect(row).toHaveCount(0, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to clean up tool ${options.id ?? options.name}`).toBe(true);
  }
}

// Re-export the agents' shadcn helper so tools tests don't depend on the
// agents fixture file path directly.
export { pickFirstSelectOption };

// ── Fill report ─────────────────────────────────────────────────────────────

export interface FillReport {
  name: boolean;
  description: boolean;
  url: boolean;
  method: boolean;
  authType: boolean;
  authHeader: boolean;
  authApiKey: boolean;
  authBearer: boolean;
  authUsername: boolean;
  authPassword: boolean;
  isActiveToggled: boolean;
  parametersAdded: number;
}
