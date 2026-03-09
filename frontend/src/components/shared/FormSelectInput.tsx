'use client';

import React from 'react';
import { Controller, type Control, type RegisterOptions } from 'react-hook-form';

import SelectInput from '@/components/shared/SelectInput';

type SelectInputProps = React.ComponentProps<typeof SelectInput>;

export interface FormSelectInputProps
  extends Omit<SelectInputProps, 'value' | 'onValueChange' | 'ref'> {
  name: string;
  control: Control<any>;
  rules?: RegisterOptions;
  onValueChange?: (value: string) => void;
}

export default function FormSelectInput({
  name,
  control,
  rules,
  onValueChange,
  ...rest
}: FormSelectInputProps) {
  return (
    <Controller
      name={name}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <SelectInput
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
