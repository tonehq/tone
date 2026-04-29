'use client';

import { cn } from '@/utils/cn';
import React, { memo } from 'react';
import { Controller } from 'react-hook-form';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { CheckboxFieldBaseProps, FormCheckboxFieldProps } from '@/types/components';

type CheckboxFieldProps = CheckboxFieldBaseProps | FormCheckboxFieldProps;

function isFormCheckbox(props: CheckboxFieldProps): props is FormCheckboxFieldProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainCheckboxField = memo(
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
  }: CheckboxFieldBaseProps) => {
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
              'cursor-pointer',
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

PlainCheckboxField.displayName = 'PlainCheckboxField';

const CheckboxField = (props: CheckboxFieldProps) => {
  if (isFormCheckbox(props)) {
    const { id, control, rules, onCheckedChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={id}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <PlainCheckboxField
            {...rest}
            id={id}
            checked={!!field.value}
            onCheckedChange={(checked) => {
              const boolVal = !!checked;
              field.onChange(boolVal);
              onCheckedChange?.(boolVal);
            }}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <PlainCheckboxField {...props} />;
};

CheckboxField.displayName = 'CheckboxField';

export default memo(CheckboxField);
