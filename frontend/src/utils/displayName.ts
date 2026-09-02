export function formatDisplayName(
  first?: string | null,
  last?: string | null,
  email?: string | null,
): string | null {
  const source = [first, last].filter(Boolean).join(' ').trim() || (email ?? '').split('@')[0];
  if (!source) return null;

  const words = source
    .split(/[._\-\s]+/)
    .filter((part) => /^[\p{L}]/u.test(part))
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase());

  return words.length ? words.join(' ') : null;
}
