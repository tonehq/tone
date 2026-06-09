'use client';

import { cn } from '@/utils/cn';
import { ChevronDown, Inbox, Loader2 } from 'lucide-react';
import React, { forwardRef } from 'react';
import { Controller } from 'react-hook-form';

import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
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
          {isEmpty && !isLoading && !isLockedRead ? (
            // Radix Select doesn't reliably open its popper when SelectContent
            // has no SelectItem children — the panel can collapse immediately
            // because there's nothing for roving focus to land on. Render a
            // Popover that mimics the trigger so the user still gets visual
            // feedback ("No data") on click.
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  id={name}
                  name={name}
                  aria-invalid={error || undefined}
                  className={cn(
                    'flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border border-input bg-background px-3.5 text-sm text-foreground shadow-sm outline-none transition-all duration-150',
                    'hover:border-foreground/20 focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20',
                    'data-[state=open]:border-primary data-[state=open]:ring-2 data-[state=open]:ring-primary/20',
                    size === 'sm' ? 'h-9' : 'h-10',
                    error &&
                      'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/20',
                    triggerClassName,
                  )}
                >
                  <span className="truncate text-left text-muted-foreground">{placeholder}</span>
                  <ChevronDown className="size-4 opacity-50" />
                </button>
              </PopoverTrigger>
              <PopoverContent
                align="start"
                sideOffset={4}
                className="flex min-w-[220px] flex-col items-center justify-center gap-1.5 px-3 py-5 text-xs text-muted-foreground"
              >
                <Inbox className="size-7 opacity-60" strokeWidth={1.25} />
                No data
              </PopoverContent>
            </Popover>
          ) : (
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
                {options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} disabled={opt.disabled}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
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
