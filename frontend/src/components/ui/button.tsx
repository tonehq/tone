import { cva, type VariantProps } from 'class-variance-authority';
import { Slot } from 'radix-ui';
import * as React from 'react';

import { cn } from '@/lib/utils';

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded text-base font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-purple-500/50 focus-visible:ring-[3px]",
  {
    variants: {
      variant: {
        default: 'bg-purple-500 text-white hover:bg-purple-600',
        destructive: 'bg-red-500 text-white hover:bg-red-600 focus-visible:ring-red-500/20',
        outline: 'border border-slate-200 bg-white shadow-xs text-gray-800 hover:bg-gray-100',
        secondary: 'bg-indigo-500 text-white hover:bg-indigo-600',
        ghost: 'text-gray-800 hover:bg-gray-100',
        link: 'text-purple-500 underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-[42px] px-4 py-2 has-[>svg]:px-3',
        xs: "h-6 gap-1 rounded-md px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: 'h-8 rounded-md gap-1.5 px-3 text-sm has-[>svg]:px-2.5',
        lg: 'h-12 rounded-md px-6 text-lg has-[>svg]:px-4',
        icon: 'size-[42px]',
        'icon-xs': "size-6 rounded-md [&_svg:not([class*='size-'])]:size-3",
        'icon-sm': 'size-8',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : 'button';

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
