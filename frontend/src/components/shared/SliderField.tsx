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
          <ControlledSlider
            {...rest}
            name={name}
            min={min}
            field={field}
            fieldError={error ?? !!fieldState.error}
            fieldHelperText={fieldState.error?.message ?? helperText}
            onValueChange={onValueChange}
          />
        )}
      />
    );
  }

  return <PlainSliderField {...props} />;
};

/**
 * Bridges RHF `Controller` and `PlainSliderField`. When the form value is
 * null/undefined — OR a non-numeric leftover such as a stale `"normal"` string
 * carried over from a provider whose same-named field was a select — the plain
 * slider visually falls back to `min`, but that value never gets pushed into RHF
 * state, so submits silently ship a value downstream validators reject
 * ("… must be a valid number"). Seed the value with `min` on mount whenever the
 * current value isn't a finite number, so the slider position and the form state
 * stay in sync and always hold a valid number.
 */
type ControlledSliderProps = Omit<SliderFieldBaseProps, 'value' | 'onValueChange'> & {
  field: {
    value: unknown;
    onChange: (value: number) => void;
  };
  fieldError: boolean;
  fieldHelperText?: string;
  onValueChange?: (value: number) => void;
};

const ControlledSlider = ({
  field,
  fieldError,
  fieldHelperText,
  onValueChange,
  min = 0,
  ...rest
}: ControlledSliderProps) => {
  const seededRef = React.useRef(false);
  React.useEffect(() => {
    // Seed `min` when the value is missing OR non-numeric (e.g. a stale string
    // from another provider). A finite number — including 0 — is left untouched.
    const isValidNumber = field.value != null && Number.isFinite(Number(field.value));
    if (!seededRef.current && !isValidNumber) {
      seededRef.current = true;
      field.onChange(min);
    }
  }, [field, min]);

  return (
    <PlainSliderField
      {...rest}
      min={min}
      value={
        field.value != null && Number.isFinite(Number(field.value)) ? Number(field.value) : min
      }
      onValueChange={(v) => {
        field.onChange(v);
        onValueChange?.(v);
      }}
      error={fieldError}
      helperText={fieldHelperText}
    />
  );
};

SliderField.displayName = 'SliderField';

export default memo(SliderField);
