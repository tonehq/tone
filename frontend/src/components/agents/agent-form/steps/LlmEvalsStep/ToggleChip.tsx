import type { ReactNode } from 'react';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';

/** Small pill-shaped toggle button used by the Run-eval modal's folder and
 * tag multi-selects. Owns the shared active/inactive pill styling so the two
 * chip groups don't each re-declare it. */
export default function ToggleChip({
  active,
  onClick,
  disabled = false,
  title,
  className,
  children,
}: {
  active: boolean;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <CustomButton
      type="text"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={active}
      className={cn(
        'h-auto rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 transition-colors',
        active
          ? 'bg-primary text-primary-foreground ring-primary hover:bg-primary'
          : 'bg-muted text-muted-foreground ring-border hover:bg-muted/80',
        disabled && 'opacity-50',
        className,
      )}
    >
      {children}
    </CustomButton>
  );
}
