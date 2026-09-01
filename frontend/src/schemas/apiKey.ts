import { z } from 'zod';

import type { ApiKeyRole } from '@/types/settings/apiKey';

/**
 * The org roles a key can carry, highest authority first. A request made with a
 * key is authorized exactly like a person of this role. The backend caps the
 * chosen role at the creating user's own role.
 */
export const API_KEY_ROLES = ['owner', 'admin', 'member', 'observer'] as const;

export const API_KEY_ROLE_LABELS: Record<ApiKeyRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  member: 'Member',
  observer: 'Observer',
};

export const API_KEY_ROLE_DESCRIPTIONS: Record<ApiKeyRole, string> = {
  owner: 'Full access, including owner-only actions',
  admin: 'Admin-level actions',
  member: 'Standard user actions only',
  observer: 'Read-only access',
};

// Authority ranking, mirrors the backend `_ROLE_RANK`. Used to hide roles above
// the creator's own so the client never offers a key it can't mint.
const ROLE_RANK: Record<string, number> = { observer: 0, member: 1, admin: 2, owner: 3 };

/** Roles the given creator role is allowed to mint a key for (its own and below). */
export function apiKeyRolesForCreator(creatorRole: string): ApiKeyRole[] {
  const cap = ROLE_RANK[creatorRole] ?? 0;
  return API_KEY_ROLES.filter((r) => ROLE_RANK[r] <= cap);
}

/**
 * The 5 expiry choices offered in the Create API Key modal. `custom` reveals a
 * DateTimePicker; `never` maps to `expires_at: null` on the wire.
 */
export const EXPIRY_CHOICES = ['7d', '30d', '60d', '90d', 'custom', 'never'] as const;
export type ExpiryChoice = (typeof EXPIRY_CHOICES)[number];

export const EXPIRY_LABELS: Record<ExpiryChoice, string> = {
  '7d': '7 days',
  '30d': '30 days',
  '60d': '60 days',
  '90d': '90 days',
  custom: 'Custom date',
  never: 'Never',
};

export const createApiKeySchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Please enter a name')
    .max(120, 'Name must be 120 characters or fewer'),
  role: z.enum(API_KEY_ROLES),
  expiry: z.enum(EXPIRY_CHOICES),
  // Only used when `expiry === 'custom'` — validated inline in the modal so the
  // Zod schema stays flexible for the other choices.
  customExpiresAt: z.string().nullable().optional(),
});

export type CreateApiKeyFormData = z.infer<typeof createApiKeySchema>;

/**
 * Convert the form's expiry choice into the ISO string the backend expects.
 * Returns `null` for `never`; throws for `custom` without a valid future date.
 */
export function expiryChoiceToIso(choice: ExpiryChoice, customIso?: string | null): string | null {
  if (choice === 'never') return null;
  if (choice === 'custom') {
    if (!customIso) throw new Error('Please pick a custom expiry date and time.');
    const when = new Date(customIso);
    if (Number.isNaN(when.getTime())) throw new Error('That expiry date is not valid.');
    if (when.getTime() <= Date.now()) throw new Error('Expiry must be in the future.');
    return when.toISOString();
  }
  const days = Number.parseInt(choice.replace('d', ''), 10);
  const when = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return when.toISOString();
}
