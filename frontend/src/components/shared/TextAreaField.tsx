'use client';

import { cn } from '@/utils/cn';
import React, { forwardRef } from 'react';

import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface TextAreaFieldProps extends Omit<React.ComponentProps<'textarea'>, 'size'> {
  name: string;
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

const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>(
  (
    {
      name,
      label,
      placeholder,
      value,
      defaultValue,
      onChange,
      isRequired = false,
      loading = false,
      disabled = false,
      error = false,
      helperText,
      className,
      labelClassName,
      rows = 3,
      ...props
    },
    ref,
  ) => {
    if (loading) {
      return (
        <div className="mb-2">
          {label && <Skeleton className="mb-1 h-4 w-20" />}
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    return (
      <>
        {label && (
          <Label htmlFor={name} className={cn('mb-1.5', labelClassName)}>
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}

        <Textarea
          ref={ref}
          id={name}
          name={name}
          placeholder={placeholder}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          disabled={disabled}
          rows={rows}
          aria-invalid={error || undefined}
          className={cn(
            'resize-none',
            error &&
              'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
            className,
          )}
          {...props}
        />

        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </>
    );
  },
);

TextAreaField.displayName = 'TextAreaField';

export default React.memo(TextAreaField);
