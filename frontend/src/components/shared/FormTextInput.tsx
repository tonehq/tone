'use client';

import React from 'react';
import { Controller, type Control, type RegisterOptions } from 'react-hook-form';

import TextInput from '@/components/shared/TextInput';

type TextInputProps = React.ComponentProps<typeof TextInput>;

export interface FormTextInputProps
  extends Omit<TextInputProps, 'value' | 'onChange' | 'onBlur' | 'ref'> {
  name: string;
  control: Control<any>;
  rules?: RegisterOptions;
  onValueChange?: (value: string) => void;
}

export default function FormTextInput({
  name,
  control,
  rules,
  onValueChange,
  ...rest
}: FormTextInputProps) {
  return (
    <Controller
      name={name}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextInput
          {...rest}
          name={name}
          value={field.value ?? ''}
          onChange={(e) => {
            field.onChange(e.target.value);
            onValueChange?.(e.target.value);
          }}
          onBlur={field.onBlur}
          error={rest.error ?? !!fieldState.error}
          helperText={rest.helperText ?? (fieldState.error?.message as string)}
        />
      )}
    />
  );
}
