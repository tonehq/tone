/**
 * Real-backend fixtures for the Model Providers / API Keys / Models e2e specs.
 *
 * Mirrors the shape of agentFixtures.ts / toolFixtures.ts / memberFixtures.ts /
 * organizationFixtures.ts: drives the real UI, namespaces every fixture with
 * the `__e2e__` prefix so leftovers from aborted runs can be swept, and
 * exposes one helper per major interaction.
 *
 * Safety:
 * - NEVER set is_default=true on a test key — the user's real agent saves
 *   pick up the default, and flipping it breaks unrelated workflows.
 * - Models are GLOBAL (no org_id column on ProviderModel). Every model the
 *   test creates is visible to every org. Always __e2e__-prefix the name
 *   and clean up in try/finally.
 */

import { expect, type Page } from '@playwright/test';

import { pickSelectOptionByLabel } from './toolFixtures';

export const E2E_PROVIDER_PREFIX = '__e2e__';

export function uniqueLabel(label: string): string {
  const safe = label.replace(/[^a-zA-Z0-9]+/g, '_');
  return `${E2E_PROVIDER_PREFIX}key_${safe}_${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
}

export function uniqueModelName(label: string): string {
  const safe = label.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase();
  return `${E2E_PROVIDER_PREFIX}model_${safe}_${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
}

export type ServiceType = 'llm' | 'stt' | 'tts';

const SERVICE_TYPE_LABELS: Record<ServiceType, string> = {
  llm: 'LLM',
  stt: 'STT',
  tts: 'TTS',
};

// ── Navigation ─────────────────────────────────────────────────────────────

export async function gotoProvidersList(page: Page): Promise<void> {
  await page.goto('/settings/model-providers');
  await expect(page.getByRole('button', { name: /add provider/i })).toBeVisible({
    timeout: 15_000,
  });
}

export async function gotoProviderDetail(
  page: Page,
  options: { providerId: string; serviceType: ServiceType },
): Promise<void> {
  await page.goto(`/settings/model-providers/${options.providerId}/${options.serviceType}`);
  await expect(page.getByRole('button', { name: /^API Keys/i }).first()).toBeVisible({
    timeout: 15_000,
  });
}

export async function gotoKeysTab(page: Page): Promise<void> {
  await page
    .getByRole('button', { name: /^API Keys/i })
    .first()
    .click();
}

export async function gotoModelsTab(page: Page): Promise<void> {
  await page
    .getByRole('button', { name: /^Models/i })
    .first()
    .click();
}

// ── Drawer openers ─────────────────────────────────────────────────────────

export async function openAddProviderDrawer(page: Page): Promise<void> {
  await page
    .getByRole('button', { name: /add provider/i })
    .first()
    .click();
  await page
    .getByRole('dialog')
    .locator('button[id="service_type"]')
    .first()
    .waitFor({ state: 'visible', timeout: 10_000 });
}

export async function openAddKeyDrawer(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Add API key', exact: true }).first().click();
  await page
    .getByRole('dialog')
    .locator('input[name="api_key"]')
    .first()
    .waitFor({ state: 'visible', timeout: 10_000 });
}

export async function openAddModelDrawer(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Add model', exact: true }).first().click();
  await page
    .getByRole('dialog')
    .locator('input[name="name"]')
    .first()
    .waitFor({ state: 'visible', timeout: 10_000 });
}

// ── Provider-catalog helpers ───────────────────────────────────────────────

/**
 * Open the provider catalog dropdown inside the currently-open Add Provider
 * drawer, pick the FIRST available provider (the test doesn't care which —
 * the catalog is read-only fixtures populated by `dev/seed.py`), and return
 * the resolved provider id from the `/services/providers/catalog` response.
 */
export async function pickFirstProviderFromCatalog(
  page: Page,
  options: { serviceType: ServiceType },
): Promise<{ providerId: string; providerName: string }> {
  // Capture the catalog response so we can resolve the id by name.
  const catalogResp = page
    .waitForResponse(
      (r) => r.url().includes('/services/providers/catalog') && r.request().method() === 'GET',
      { timeout: 10_000 },
    )
    .catch(() => null);

  // Pick the service type first — provider dropdown is filtered by it.
  const dialog = page.getByRole('dialog');
  const typeTrigger = dialog.locator('button[id="service_type"]').first();
  await pickSelectOptionByLabel(page, typeTrigger, SERVICE_TYPE_LABELS[options.serviceType]);
  // Service-type change may re-fetch the catalog; wait for it if so.
  const response = await catalogResp;

  // Open the provider dropdown and pick the first option.
  const providerTrigger = dialog.locator('button[id="provider_id"]').first();
  await providerTrigger.click();
  const listbox = page.getByRole('listbox').first();
  const firstOption = listbox.getByRole('option').first();
  await firstOption.waitFor({ state: 'visible', timeout: 5_000 });
  const providerName = (await firstOption.textContent())?.trim() ?? '';
  await firstOption.click();

  // Resolve the id by matching display_name against the catalog response.
  let providerId = '';
  if (response) {
    try {
      const catalog = (await response.json()) as Array<{
        id: string;
        display_name?: string;
        name?: string;
      }>;
      const row = catalog.find(
        (c) =>
          (c.display_name && providerName.startsWith(c.display_name)) ||
          (c.name && providerName.startsWith(c.name)),
      );
      if (row) providerId = row.id;
    } catch {
      // Fall through — providerId stays empty; caller will throw if needed.
    }
  }
  return { providerId, providerName };
}

// ── API Key CRUD via UI ────────────────────────────────────────────────────

export interface CreateKeyValues {
  serviceType: ServiceType;
  label?: string;
  secret?: string;
  description?: string;
}

/**
 * Create an API key for the first available provider of the given
 * service_type. Returns the resolved `{ id, providerId, providerName, label }`
 * for cleanup. NEVER sets is_default=true (see safety note at file top).
 */
export async function createApiKeyViaUI(
  page: Page,
  values: CreateKeyValues,
): Promise<{ id: string; providerId: string; providerName: string; label: string }> {
  const label = values.label ?? uniqueLabel('default');
  const secret = values.secret ?? `sk-e2e-test-${Date.now()}`;
  const description = values.description ?? 'E2E fixture — safe to delete.';

  await gotoProvidersList(page);
  await openAddProviderDrawer(page);
  const { providerId, providerName } = await pickFirstProviderFromCatalog(page, {
    serviceType: values.serviceType,
  });
  const dialog = page.getByRole('dialog');
  await dialog.locator('input[name="label"]').first().fill(label);
  await dialog.locator('textarea#description').first().fill(description);
  await dialog.locator('input[name="api_key"]').first().fill(secret);

  // Capture the create response so we can return the new key id.
  const createResp = page
    .waitForResponse((r) => r.url().endsWith('/services') && r.request().method() === 'POST', {
      timeout: 15_000,
    })
    .catch(() => null);
  await dialog.getByRole('button', { name: /^create$/i }).click();
  const resp = await createResp;

  await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10_000 });

  let id = '';
  if (resp) {
    try {
      const body = (await resp.json()) as { id?: string };
      id = body.id ?? '';
    } catch {
      // ignore
    }
  }
  return { id, providerId, providerName, label };
}

/**
 * Best-effort delete a single API key by label. Visits the detail page for
 * the (provider, service_type) pair, finds the row by label text, opens the
 * confirm modal, confirms. Swallows errors so a teardown failure never
 * fails a test that already passed.
 */
export async function deleteApiKeyViaUI(
  page: Page,
  options: { providerId: string; serviceType: ServiceType; label: string },
): Promise<void> {
  try {
    await gotoProviderDetail(page, {
      providerId: options.providerId,
      serviceType: options.serviceType,
    });
    await gotoKeysTab(page);
    const row = page.locator('tbody tr').filter({ hasText: options.label }).first();
    if (!(await row.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await row.getByRole('button', { name: 'Delete API key', exact: true }).click({ force: true });
    const confirm = page
      .getByRole('dialog')
      .getByRole('button', { name: /^delete$/i })
      .last();
    if (await confirm.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await confirm.click();
    }
    await expect(row).toHaveCount(0, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to delete API key "${options.label}"`).toBe(true);
  }
}

// ── Provider Model CRUD via UI ─────────────────────────────────────────────

export interface CreateModelValues {
  kind: ServiceType;
  name?: string;
  displayName?: string;
  description?: string;
}

const KIND_LABELS: Record<ServiceType, string> = {
  llm: 'LLM',
  stt: 'STT',
  tts: 'TTS',
};

/**
 * Create a provider-model row for the given providerId. The caller must
 * already be on a detail page for that provider; the helper opens the
 * Add model drawer, fills, submits, waits for the success toast.
 */
export async function createProviderModelViaUI(
  page: Page,
  values: CreateModelValues & { providerId: string; serviceType: ServiceType },
): Promise<{ name: string; displayName: string }> {
  const name = values.name ?? uniqueModelName('fixture');
  const displayName = values.displayName ?? '';
  const description = values.description ?? 'E2E fixture — safe to delete.';

  await gotoProviderDetail(page, {
    providerId: values.providerId,
    serviceType: values.serviceType,
  });
  await gotoModelsTab(page);
  await openAddModelDrawer(page);
  const dialog = page.getByRole('dialog');
  await dialog.locator('input[name="name"]').first().fill(name);
  if (displayName) {
    await dialog.locator('input[name="display_name"]').first().fill(displayName);
  }
  const kindTrigger = dialog.locator('button[id="kind"]').first();
  await pickSelectOptionByLabel(page, kindTrigger, KIND_LABELS[values.kind]);
  await dialog.locator('textarea#description').first().fill(description);

  await dialog.getByRole('button', { name: /^save$/i }).click();
  await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10_000 });
  return { name, displayName };
}

/**
 * Best-effort delete a provider-model by name. Swallows errors.
 */
export async function deleteProviderModelViaUI(
  page: Page,
  options: { providerId: string; serviceType: ServiceType; name: string },
): Promise<void> {
  try {
    await gotoProviderDetail(page, {
      providerId: options.providerId,
      serviceType: options.serviceType,
    });
    await gotoModelsTab(page);
    const row = page.locator('tbody tr').filter({ hasText: options.name }).first();
    if (!(await row.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await row.getByRole('button', { name: 'Delete model', exact: true }).click({ force: true });
    const confirm = page
      .getByRole('dialog')
      .getByRole('button', { name: /^delete$/i })
      .last();
    if (await confirm.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await confirm.click();
    }
    await expect(row).toHaveCount(0, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to delete model "${options.name}"`).toBe(true);
  }
}

// Re-exports for convenience.
export { pickSelectOptionByLabel };
