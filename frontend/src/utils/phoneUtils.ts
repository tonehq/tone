import { COUNTRY_CODES_SORTED, type CountryCode } from '@/constants/countryCodes';

/**
 * Detect which country a phone number belongs to by matching its dial-code prefix.
 * Returns the first (most-specific) match, or `null` if none found.
 *
 * The phone number can start with "+" or without. Spaces, dashes, and parentheses
 * are stripped before matching.
 */
export function detectCountryFromPhone(phoneNumber: string): CountryCode | null {
  if (!phoneNumber) return null;

  // Normalise: keep only digits and leading +
  const cleaned = phoneNumber.replace(/[^\d+]/g, '');
  const withPlus = cleaned.startsWith('+') ? cleaned : `+${cleaned}`;

  for (const country of COUNTRY_CODES_SORTED) {
    if (withPlus.startsWith(country.dialCode)) {
      return country;
    }
  }

  return null;
}

/**
 * Extract just the ISO-2 country code from a phone number.
 * Falls back to `null` when no match is found.
 */
export function getCountryIso2FromPhone(phoneNumber: string): string | null {
  return detectCountryFromPhone(phoneNumber)?.iso2 ?? null;
}

/**
 * Format a phone number as `+CC-LOCALNUM` (e.g. `+1-2025551234`, `+91-9876543210`).
 * If no country code is detected the original string is returned unchanged.
 */
export function formatPhoneWithDash(phoneNumber: string): string {
  if (!phoneNumber) return phoneNumber;

  const country = detectCountryFromPhone(phoneNumber);
  if (!country) return phoneNumber;

  const cleaned = phoneNumber.replace(/[^\d+]/g, '');
  const withPlus = cleaned.startsWith('+') ? cleaned : `+${cleaned}`;
  const localPart = withPlus.slice(country.dialCode.length);

  if (!localPart) return phoneNumber;

  return `${country.dialCode}-${localPart}`;
}
