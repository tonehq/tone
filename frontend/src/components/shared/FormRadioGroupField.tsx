'use client';

import React from 'react';
import { Controller, type Control, type RegisterOptions } from 'react-hook-form';

import RadioGroupField from '@/components/shared/RadioGroupField';

type RadioGroupFieldProps = React.ComponentProps<typeof RadioGroupField>;

export interface FormRadioGroupFieldProps
  extends Omit<RadioGroupFieldProps, 'value' | 'onValueChange' | 'ref'> {
  name: string;
  control: Control<any>;
  rules?: RegisterOptions;
  onValueChange?: (value: string) => void;
}

export default function FormRadioGroupField({
  name,
  control,
  rules,
  onValueChange,
  ...rest
}: FormRadioGroupFieldProps) {
  return (
    <Controller
      name={name}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <RadioGroupField
          {...rest}
          name={name}
          value={field.value != null ? String(field.value) : ''}
          onValueChange={(v) => {
            field.onChange(v);
            onValueChange?.(v);
          }}
          error={rest.error ?? !!fieldState.error}
          helperText={rest.helperText ?? (fieldState.error?.message as string)}
        />
      )}
    />
  );
}
