'use client';

import { cn } from '@/utils/cn';
import React, { memo } from 'react';
import { Controller } from 'react-hook-form';

import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import type { FormSliderFieldProps, SliderFieldBaseProps } from '@/types/components';

type SliderFieldProps = SliderFieldBaseProps | FormSliderFieldProps;

function isFormSlider(props: SliderFieldProps): props is FormSliderFieldProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainSliderField = memo(
  ({
    name,
    value,
    onValueChange,
    min = 0,
    max = 100,
    step = 1,
    label,
    isRequired = false,
    loading = false,
    error = false,
    helperText,
    labelClassName,
    className,
    disabled = false,
    showLabels = true,
  }: SliderFieldBaseProps) => {
    const currentValue = value != null ? value : min;

    if (loading) {
      return (
        <div className="mb-2">
          {label && <Skeleton className="mb-1 h-4 w-20" />}
          <Skeleton className="h-4 w-full" />
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
        <div className="w-full px-1">
          <Slider
            value={[currentValue]}
            onValueChange={([v]) => onValueChange?.(v)}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            aria-invalid={error || undefined}
          />
          {showLabels && (
            <div className="mt-1 flex justify-between text-xs text-muted-foreground">
              <span>{min}</span>
              <span>{currentValue}</span>
              <span>{max}</span>
            </div>
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

PlainSliderField.displayName = 'PlainSliderField';

const SliderField = (props: SliderFieldProps) => {
  if (isFormSlider(props)) {
    const { name, control, rules, onValueChange, error, helperText, min = 0, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <PlainSliderField
            {...rest}
            name={name}
            min={min}
            value={field.value != null ? Number(field.value) : min}
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

  return <PlainSliderField {...props} />;
};

SliderField.displayName = 'SliderField';

export default memo(SliderField);
