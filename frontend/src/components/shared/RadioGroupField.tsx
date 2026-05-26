'use client';

import { cn } from '@/utils/cn';
import { Loader2 } from 'lucide-react';
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
    // While options load, render the label with an inline spinner instead of
    // a skeleton swap so the layout stays put (matches the SelectInput pattern
    // used in the agent create/edit flow).
    if (loading) {
      return (
        <div className="mb-2 flex flex-col gap-2">
          {label && (
            <Label className={cn('flex items-center gap-2', labelClassName)}>
              {label}
              {isRequired && <span className="ml-0.5 text-destructive">*</span>}
              <Loader2
                className="size-3 animate-spin text-muted-foreground"
                aria-label="Loading options"
              />
            </Label>
          )}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3 animate-spin" />
            Loading options...
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
