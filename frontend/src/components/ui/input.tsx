import * as React from 'react';

import { cn } from '@/utils/cn';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'h-10 w-full min-w-0 rounded-lg border border-input bg-background px-3.5 text-sm text-foreground shadow-sm outline-none transition-all duration-150',
        'placeholder:text-muted-foreground/60',
        'hover:border-foreground/20',
        'focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20',
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20',
        className,
      )}
      {...props}
    />
  );
}

export { Input };
