'use client';

import { cn } from '@/utils/cn';
import { formatPhoneWithDash, getCountryIso2FromPhone } from '@/utils/phoneUtils';
import * as FlagIcons from 'country-flag-icons/react/3x2';

type FlagKey = keyof typeof FlagIcons;

interface PhoneNumberDisplayProps {
  phoneNumber: string;
  className?: string;
  flagSize?: 'sm' | 'md' | 'lg';
  showCountryCode?: boolean;
}

const FLAG_SIZES = {
  sm: 'h-3 w-[18px]',
  md: 'h-4 w-6',
  lg: 'h-5 w-[30px]',
} as const;

/**
 * Renders a phone number with its country flag.
 * Automatically detects the country from the dial-code prefix.
 */
export function PhoneNumberDisplay({
  phoneNumber,
  className,
  flagSize = 'md',
  showCountryCode: _showCountryCode,
}: PhoneNumberDisplayProps) {
  if (!phoneNumber) return <span className="text-muted-foreground">—</span>;

  const iso2 = getCountryIso2FromPhone(phoneNumber);
  const FlagComponent = iso2
    ? (FlagIcons[iso2 as FlagKey] as React.ComponentType<React.SVGProps<SVGSVGElement>> | undefined)
    : undefined;

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      {FlagComponent ? (
        <FlagComponent
          className={cn('shrink-0 rounded-[2px] object-cover', FLAG_SIZES[flagSize])}
          aria-label={iso2 ?? undefined}
        />
      ) : (
        <span
          className={cn(
            'inline-flex shrink-0 items-center justify-center rounded-[2px] bg-muted text-[9px] font-medium text-muted-foreground',
            FLAG_SIZES[flagSize],
          )}
        >
          ?
        </span>
      )}
      <span className="text-sm">{formatPhoneWithDash(phoneNumber)}</span>
    </span>
  );
}
