'use client';

import { cn } from '@/utils/cn';
import React, { forwardRef } from 'react';
import { Controller } from 'react-hook-form';

import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { FormSelectInputProps, SelectInputBaseProps, SelectOption } from '@/types/components';

export type { SelectOption };

type SelectInputProps = SelectInputBaseProps | FormSelectInputProps;

function isFormSelect(props: SelectInputProps): props is FormSelectInputProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainSelectInput = forwardRef<HTMLButtonElement, SelectInputBaseProps>(
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
      position,
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
          <SelectContent position={position}>
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

PlainSelectInput.displayName = 'PlainSelectInput';

const MemoizedPlainSelectInput = React.memo(PlainSelectInput);

const SelectInput = forwardRef<HTMLButtonElement, SelectInputProps>((props, ref) => {
  if (isFormSelect(props)) {
    const { name, control, rules, onValueChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <MemoizedPlainSelectInput
            {...rest}
            name={name}
            value={field.value != null ? String(field.value) : ''}
            onValueChange={(v) => {
              field.onChange(v);
              onValueChange?.(v);
            }}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <MemoizedPlainSelectInput ref={ref} {...props} />;
});

SelectInput.displayName = 'SelectInput';

export default React.memo(SelectInput);
