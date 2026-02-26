'use client';

import { cn } from '@/lib/utils';
import React, { memo } from 'react';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';

interface CheckboxFieldProps extends Omit<React.ComponentProps<typeof Checkbox>, 'id'> {
  id: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const CheckboxField = memo(
  ({
    id,
    label,
    isRequired = false,
    loading = false,
    error = false,
    helperText,
    labelClassName,
    className,
    disabled = false,
    ...props
  }: CheckboxFieldProps) => {
    if (loading) {
      return (
        <div className="mb-2">
          <div className="flex items-center gap-2">
            <Skeleton className="size-4 shrink-0 rounded-sm" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
      );
    }

    return (
      <>
        <div className="flex items-center gap-2">
          <Checkbox
            id={id}
            disabled={disabled}
            aria-invalid={error || undefined}
            aria-required={isRequired || undefined}
            className={cn(
              error &&
                'border-destructive data-[state=checked]:bg-destructive/90 focus-visible:ring-destructive/20',
              className,
            )}
            {...props}
          />
          {label && (
            <Label
              htmlFor={id}
              className={cn(
                'text-sm font-normal cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
                labelClassName,
              )}
            >
              {label}
              {isRequired && <span className="ml-0.5 text-destructive">*</span>}
            </Label>
          )}
        </div>
        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </>
    );
  },
);

CheckboxField.displayName = 'CheckboxField';

export default CheckboxField;
