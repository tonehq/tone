'use client';

import { Circle } from 'lucide-react';
import { RadioGroup as RadioGroupPrimitive } from 'radix-ui';
import * as React from 'react';

import { cn } from '@/lib/utils';

const RadioGroup = React.forwardRef<
  React.ComponentRef<typeof RadioGroupPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>
>(({ className, ...props }, ref) => (
  <RadioGroupPrimitive.Root
    ref={ref}
    data-slot="radio-group"
    className={cn('grid gap-2', className)}
    {...props}
  />
));
RadioGroup.displayName = RadioGroupPrimitive.Root.displayName;

const RadioGroupItem = React.forwardRef<
  React.ComponentRef<typeof RadioGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>
>(({ className, ...props }, ref) => (
  <RadioGroupPrimitive.Item
    ref={ref}
    data-slot="radio-group-item"
    className={cn(
      'aspect-square size-4 rounded-full border border-primary text-primary shadow-xs',
      'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[2px] focus-visible:outline-none',
      'disabled:cursor-not-allowed disabled:opacity-50',
      'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
      className,
    )}
    {...props}
  >
    <RadioGroupPrimitive.Indicator
      data-slot="radio-group-indicator"
      className="flex items-center justify-center text-current"
    >
      <Circle className="size-2.5 fill-current" />
    </RadioGroupPrimitive.Indicator>
  </RadioGroupPrimitive.Item>
));
RadioGroupItem.displayName = RadioGroupPrimitive.Item.displayName;

export { RadioGroup, RadioGroupItem };
