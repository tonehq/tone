'use client';

import { cn } from '@/lib/utils';
import React, { forwardRef } from 'react';

import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectInputProps {
  name: string;
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  className?: string;
  triggerClassName?: string;
  size?: 'sm' | 'default';
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const SelectInput = forwardRef<HTMLButtonElement, SelectInputProps>(
  (
    {
      name,
      options,
      value,
      defaultValue,
      onValueChange,
      placeholder = 'Select an option',
      label,
      isRequired = false,
      loading = false,
      disabled = false,
      error = false,
      helperText,
      labelClassName,
      className,
      triggerClassName,
      size = 'default',
    },
    ref,
  ) => {
    if (loading) {
      return (
        <div className="mb-2">
          {label && <Skeleton className="mb-1 h-4 w-20" />}
          <Skeleton className="h-9 w-full" />
        </div>
      );
    }

    return (
      <div className={className}>
        {label && (
          <Label htmlFor={name} className={cn('mb-1.5', labelClassName)}>
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}

        <Select
          value={value}
          defaultValue={defaultValue}
          onValueChange={onValueChange}
          disabled={disabled}
          name={name}
        >
          <SelectTrigger
            ref={ref}
            id={name}
            size={size}
            aria-invalid={error || undefined}
            className={cn(
              'w-full',
              error &&
                'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
              triggerClassName,
            )}
          >
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value} disabled={opt.disabled}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

SelectInput.displayName = 'SelectInput';

export default React.memo(SelectInput);
