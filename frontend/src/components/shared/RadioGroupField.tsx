'use client';

import { cn } from '@/utils/cn';
import React, { memo } from 'react';
import { Controller } from 'react-hook-form';

import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import type {
  FormRadioGroupFieldProps,
  RadioGroupFieldBaseProps,
  RadioGroupOption,
} from '@/types/components';

export type { RadioGroupOption };

type RadioGroupFieldProps = RadioGroupFieldBaseProps | FormRadioGroupFieldProps;

function isFormRadioGroup(props: RadioGroupFieldProps): props is FormRadioGroupFieldProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainRadioGroupField = React.forwardRef<
  React.ComponentRef<typeof RadioGroup>,
  RadioGroupFieldBaseProps
>(
  (
    {
      name,
      label,
      options,
      value,
      defaultValue,
      onValueChange,
      isRequired = false,
      loading = false,
      error = false,
      helperText,
      labelClassName,
      orientation = 'vertical',
      disabled = false,
      className,
      ...props
    },
    ref,
  ) => {
    if (loading) {
      return (
        <div className="mb-2">
          <Skeleton className="mb-2 h-4 w-24" />
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-2">
                <Skeleton className="size-4 shrink-0 rounded-full" />
                <Skeleton className="h-4 w-32" />
              </div>
            ))}
          </div>
        </div>
      );
    }

    return (
      <>
        {label && (
          <Label
            className={cn('mb-2 block', labelClassName)}
            aria-required={isRequired || undefined}
          >
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}
        <RadioGroup
          ref={ref}
          name={name}
          value={value}
          defaultValue={defaultValue}
          onValueChange={onValueChange}
          disabled={disabled}
          required={isRequired}
          aria-invalid={error || undefined}
          aria-required={isRequired || undefined}
          className={cn(
            orientation === 'horizontal' && 'flex flex-row flex-wrap gap-4',
            orientation === 'vertical' && 'grid gap-2',
            className,
          )}
          {...props}
        >
          {options.map((option) => (
            <div
              key={option.value}
              className={cn(
                'flex items-center gap-2',
                orientation === 'horizontal' && 'flex items-center gap-2',
              )}
            >
              <RadioGroupItem
                value={option.value}
                id={`${name}-${option.value}`}
                disabled={option.disabled ?? disabled}
                aria-invalid={error || undefined}
              />
              <Label
                htmlFor={`${name}-${option.value}`}
                className={cn(
                  'cursor-pointer text-sm font-normal peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
                  (option.disabled ?? disabled) && 'cursor-not-allowed opacity-70',
                )}
              >
                {option.label}
              </Label>
            </div>
          ))}
        </RadioGroup>
        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </>
    );
  },
);

PlainRadioGroupField.displayName = 'PlainRadioGroupField';

const MemoizedPlainRadioGroupField = memo(PlainRadioGroupField);

const RadioGroupField = React.forwardRef<
  React.ComponentRef<typeof RadioGroup>,
  RadioGroupFieldProps
>((props, ref) => {
  if (isFormRadioGroup(props)) {
    const { name, control, rules, onValueChange, transformValue, error, helperText, ...rest } =
      props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <MemoizedPlainRadioGroupField
            {...rest}
            name={name}
            value={field.value != null ? String(field.value) : ''}
            onValueChange={(v) => {
              field.onChange(transformValue ? transformValue(v) : v);
              onValueChange?.(v);
            }}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <MemoizedPlainRadioGroupField ref={ref} {...props} />;
});

RadioGroupField.displayName = 'RadioGroupField';

export default memo(RadioGroupField);
