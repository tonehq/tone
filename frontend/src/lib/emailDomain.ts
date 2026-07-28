// Business-only email guard shared by every signup / invite Zod schema.
// Mirrors the backend guard in `core/utils/email_domain.py` — server is the
// source of truth; this file exists only so the user sees an inline error
// before submit rather than a 400 round-trip. Format validation (`.email()`)
// happens upstream in the caller's Zod schema.

import disposableDomains from 'disposable-email-domains';

// Hand-curated free-mail providers we block for B2B signups. Keep in sync
// with `PERSONAL_EMAIL_DOMAINS` in the backend helper. All entries lowercase.
const PERSONAL_EMAIL_DOMAINS: ReadonlySet<string> = new Set([
  // Google
  'gmail.com',
  'googlemail.com',
  // Yahoo
  'yahoo.com',
  'yahoo.co.in',
  'yahoo.co.uk',
  'ymail.com',
  'rocketmail.com',
  // Microsoft
  'outlook.com',
  'outlook.in',
  'hotmail.com',
  'hotmail.co.uk',
  'live.com',
  'msn.com',
  // Apple
  'icloud.com',
  'me.com',
  'mac.com',
  // Other consumer providers
  'aol.com',
  'proton.me',
  'protonmail.com',
  'pm.me',
  'gmx.com',
  'gmx.net',
  'gmx.de',
  'mail.com',
  'yandex.com',
  'yandex.ru',
  'tutanota.com',
  'tuta.io',
  'fastmail.com',
  'zoho.com',
  // Regional consumer providers
  'qq.com',
  '163.com',
  '126.com',
  'sina.com',
  'rediffmail.com',
]);

// The npm package ships an array; build a Set once for O(1) lookups.
const DISPOSABLE_EMAIL_DOMAINS: ReadonlySet<string> = new Set(disposableDomains);

export const PERSONAL_EMAIL_ERROR =
  "Please use your company email address. Personal email addresses (Gmail, Yahoo, Outlook, etc.) aren't allowed.";

function extractDomain(email: string): string {
  if (!email || !email.includes('@')) return '';
  const domain = email.split('@').pop();
  return domain ? domain.trim().toLowerCase() : '';
}

export function isPersonalEmail(email: string): boolean {
  const domain = extractDomain(email);
  if (!domain) return false;
  return PERSONAL_EMAIL_DOMAINS.has(domain) || DISPOSABLE_EMAIL_DOMAINS.has(domain);
}

// Zod-friendly predicate: passes when the address is a business email OR when
// the field is empty (empty is treated as "no value yet" so required-checks
// stay isolated in the caller's `.min(1)` rule).
export function isBusinessEmail(email: string): boolean {
  if (!email) return true;
  return !isPersonalEmail(email);
}
