import type { ReactNode } from 'react';

import { cn } from '@/utils/cn';

// The one rounded status pill shared by ``VerdictChip`` and
// ``VersionStatusChip`` — an icon + label tinted by the caller's ``className``.
// Each caller owns its status→style lookup; this owns the pill shape so the
// chips can't drift.
export default function StatusPill({
  icon,
  label,
  className,
}: {
  icon: ReactNode;
  label: ReactNode;
  className: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        className,
      )}
    >
      {icon}
      {label}
    </span>
  );
}
