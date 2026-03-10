'use client';

import { cn } from '@/utils/cn';
import { X } from 'lucide-react';
import React, { memo, useState } from 'react';
import { Controller } from 'react-hook-form';

import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { FormMultiSelectFieldProps, MultiSelectFieldBaseProps } from '@/types/components';

type MultiSelectFieldProps = MultiSelectFieldBaseProps | FormMultiSelectFieldProps;

function isFormMultiSelect(props: MultiSelectFieldProps): props is FormMultiSelectFieldProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainMultiSelectField = memo(
  ({
    name,
    options,
    value = [],
    onChange,
    placeholder,
    label,
    isRequired = false,
    loading = false,
    error = false,
    helperText,
    labelClassName,
    className,
    disabled = false,
  }: MultiSelectFieldBaseProps) => {
    const [tagInput, setTagInput] = useState('');
    const selectedValues = Array.isArray(value) ? value : [];

    if (loading) {
      return (
        <div className="mb-2">
          {label && <Skeleton className="mb-1 h-4 w-20" />}
          <Skeleton className="h-9 w-full" />
        </div>
      );
    }

    const content =
      options && options.length > 0 ? (
        <div className="flex flex-col gap-2">
          {options.map((opt) => {
            const isChecked = selectedValues.includes(opt.value);
            return (
              <div key={opt.value} className="flex items-center gap-2">
                <Checkbox
                  id={`${name}-${opt.value}`}
                  checked={isChecked}
                  disabled={disabled}
                  onCheckedChange={(checked) => {
                    const next = checked
                      ? [...selectedValues, opt.value]
                      : selectedValues.filter((v) => v !== opt.value);
                    onChange?.(next);
                  }}
                  aria-invalid={error || undefined}
                  className={cn(
                    error &&
                      'border-destructive data-[state=checked]:bg-destructive/90 focus-visible:ring-destructive/20',
                  )}
                />
                <Label
                  htmlFor={`${name}-${opt.value}`}
                  className="cursor-pointer text-sm font-normal peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  {opt.label}
                </Label>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Input
              name={`${name}-input`}
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  const trimmed = tagInput.trim();
                  if (trimmed && !selectedValues.includes(trimmed)) {
                    onChange?.([...selectedValues, trimmed]);
                    setTagInput('');
                  }
                }
              }}
              disabled={disabled}
              placeholder={placeholder ?? `Add ${name}`}
              aria-invalid={error || undefined}
              className={cn(
                error &&
                  'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
              )}
            />
          </div>
          {selectedValues.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedValues.map((val) => (
                <span
                  key={val}
                  className="inline-flex items-center gap-1 rounded-md border bg-muted px-2 py-0.5 text-xs"
                >
                  {val}
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onChange?.(selectedValues.filter((v) => v !== val))}
                    className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      );

    return (
      <div className={className}>
        {label && (
          <Label className={cn('mb-1.5', labelClassName)}>
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}
        {content}
        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

PlainMultiSelectField.displayName = 'PlainMultiSelectField';

const MultiSelectField = (props: MultiSelectFieldProps) => {
  if (isFormMultiSelect(props)) {
    const { name, control, rules, onChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <PlainMultiSelectField
            {...rest}
            name={name}
            value={Array.isArray(field.value) ? field.value : []}
            onChange={(v) => {
              field.onChange(v);
              onChange?.(v);
            }}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <PlainMultiSelectField {...props} />;
};

MultiSelectField.displayName = 'MultiSelectField';

export default memo(MultiSelectField);
