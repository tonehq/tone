import * as React from 'react';

import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'placeholder:text-gray-400 border-slate-200 h-[42px] w-full min-w-0 rounded border bg-gray-50 px-2.5 text-base text-gray-800 shadow-xs transition-[color,box-shadow] outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-gray-100',
        'focus-visible:border-purple-500 focus-visible:ring-purple-500/50 focus-visible:ring-[2px]',
        'aria-invalid:ring-red-500/20 aria-invalid:border-red-500',
        className,
      )}
      {...props}
    />
  );
}

export { Input };
