'use client';

import { cn } from '@/utils/cn';
import { Loader2 } from 'lucide-react';
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
    // While the options are loading we keep the trigger mounted (no skeleton
    // swap) so the field doesn't jump. The chevron is hidden via the
    // aria-busy attribute selector and we overlay a spinner in its place.
    const isLoading = loading;
    const isEmpty = !isLoading && options.length === 0;
    const isDisabled = disabled || isLoading;
    // The "locked-because-the-value-is-already-decided" look (e.g. Type field
    // pre-filled from the catalog tile). Distinct from loading: keep the
    // chevron visible but mute the surface so the user reads it as read-only.
    const isLockedRead = disabled && !isLoading;

    return (
      <div className={className}>
        {label && (
          <Label htmlFor={name} className={cn('mb-1.5', labelClassName)}>
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}

        <div className="relative">
          <Select
            value={value}
            defaultValue={defaultValue}
            onValueChange={onValueChange}
            disabled={isDisabled}
            name={name}
          >
            <SelectTrigger
              ref={ref}
              id={name}
              size={size}
              aria-invalid={error || undefined}
              aria-busy={isLoading || undefined}
              className={cn(
                'w-full',
                !isDisabled && 'cursor-pointer',
                isLoading &&
                  'cursor-progress text-muted-foreground [&[aria-busy=true]_svg]:invisible',
                isLockedRead &&
                  'bg-muted/50 text-foreground/80 disabled:cursor-not-allowed disabled:opacity-100',
                error &&
                  'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
                triggerClassName,
              )}
            >
              {isLoading ? (
                <span className="text-sm text-muted-foreground">Loading...</span>
              ) : (
                <SelectValue placeholder={placeholder} />
              )}
            </SelectTrigger>
            <SelectContent position={position}>
              {isEmpty ? (
                <div className="px-3 py-2 text-center text-xs text-muted-foreground">
                  No items to select
                </div>
              ) : (
                options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} disabled={opt.disabled}>
                    {opt.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          {isLoading && (
            <Loader2
              aria-hidden
              className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
            />
          )}
        </div>

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
