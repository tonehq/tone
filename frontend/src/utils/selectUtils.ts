/**
 * Utility for generating select options from any array of objects.
 *
 * Maps `valueKey` → `value` and `labelKey` → `label`, and spreads all
 * remaining properties from the source item into the option object.
 *
 * @example
 * // Simple provider options
 * toSelectOptions(providers, { valueKey: 'id', labelKey: 'display_name' })
 * // → [{ value: '1', label: 'ElevenLabs', id: 1, uuid: '...', ... }]
 *
 * @example
 * // With custom formatters
 * toSelectOptions(languages, {
 *   valueKey: 'value',
 *   labelKey: 'label',
 *   labelFormatter: (item) => `${item.flag} ${item.label}`,
 * })
 * // → [{ value: 'en', label: '🇺🇸 English', flag: '🇺🇸', ... }]
 *
 * @example
 * // With custom value formatter
 * toSelectOptions(models, {
 *   valueKey: 'name',
 *   labelKey: 'name',
 *   valueFormatter: (m) => m.meta_data?.model ?? m.name,
 * })
 */
export function toSelectOptions<T extends object>(
  items: T[],
  config: {
    valueKey: keyof T;
    labelKey: keyof T;
    labelFormatter?: (item: T) => string;
    valueFormatter?: (item: T) => string;
  },
): ({ value: string; label: string } & T)[] {
  const { valueKey, labelKey, labelFormatter, valueFormatter } = config;
  return items.map((item) => ({
    ...item,
    value: valueFormatter ? valueFormatter(item) : String(item[valueKey]),
    label: labelFormatter ? labelFormatter(item) : String(item[labelKey]),
  })) as ({ value: string; label: string } & T)[];
}
