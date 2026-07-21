// Constants for the contact-schema field editor (shared, single source of truth).

/**
 * Date/time formats offered in the schema field editor's "Date/time format" dropdown. Every
 * option carries BOTH a date AND a time component (a datetime field always has both). `label`
 * is human-readable; `value` is the Python `strptime` format the importer uses — so users
 * pick a format instead of hand-writing `%`-directives. Add a format here (one place) and
 * every schema field editor gets it.
 */
export const DATETIME_FORMAT_OPTIONS: { value: string; label: string }[] = [
  { value: '%Y-%m-%d %H:%M:%S', label: 'YYYY-MM-DD HH:MM:SS (24h)' },
  { value: '%Y-%m-%d %H:%M', label: 'YYYY-MM-DD HH:MM (24h)' },
  { value: '%m/%d/%Y %H:%M', label: 'MM/DD/YYYY HH:MM (24h)' },
  { value: '%d/%m/%Y %H:%M', label: 'DD/MM/YYYY HH:MM (24h)' },
  { value: '%m/%d/%Y %I:%M %p', label: 'MM/DD/YYYY hh:MM AM/PM' },
  { value: '%d/%m/%Y %I:%M %p', label: 'DD/MM/YYYY hh:MM AM/PM' },
];

/** Default selection for a new datetime field (the first offered format). */
export const DEFAULT_DATETIME_FORMAT = DATETIME_FORMAT_OPTIONS[0].value;
