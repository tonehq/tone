'use client';

import React, { useMemo } from 'react';

import SearchableSelect, {
  type SearchableSelectOption,
} from '@/components/shared/SearchableSelect';
import { getBrowserTimeZone, getTimeZones } from '@/utils/date';

interface TimezoneSelectProps {
  value?: string;
  onValueChange: (value: string) => void;
  name?: string;
  label?: string;
  isRequired?: boolean;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Shared searchable IANA timezone picker — the single source of the timezone dropdown
 * (options built once from `getTimeZones()`, with the browser zone ensured present).
 * Reused by the DateTimePicker, the org scheduling-timezone setting, and datetime schema
 * fields so the zone list/behaviour is never re-implemented.
 */
const TimezoneSelect: React.FC<TimezoneSelectProps> = ({
  value,
  onValueChange,
  name = 'timezone',
  label,
  isRequired,
  disabled,
  loading,
  placeholder = 'Select timezone',
  className,
}) => {
  const options = useMemo<SearchableSelectOption[]>(() => {
    const zones = getTimeZones();
    const browser = getBrowserTimeZone();
    if (!zones.includes(browser)) zones.unshift(browser);
    return zones.map((z) => ({ value: z, label: z.replace(/_/g, ' ') }));
  }, []);

  return (
    <SearchableSelect
      name={name}
      options={options}
      value={value}
      onValueChange={onValueChange}
      label={label}
      isRequired={isRequired}
      disabled={disabled}
      loading={loading}
      placeholder={placeholder}
      searchPlaceholder="Search timezone..."
      className={className}
    />
  );
};

export default React.memo(TimezoneSelect);
