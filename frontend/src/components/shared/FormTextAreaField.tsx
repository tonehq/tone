'use client';

import React from 'react';
import { Controller, type Control, type RegisterOptions } from 'react-hook-form';

import TextAreaField from '@/components/shared/TextAreaField';

type TextAreaFieldProps = React.ComponentProps<typeof TextAreaField>;

export interface FormTextAreaFieldProps
  extends Omit<TextAreaFieldProps, 'value' | 'onChange' | 'onBlur' | 'ref'> {
  name: string;
  control: Control<any>;
  rules?: RegisterOptions;
  onValueChange?: (value: string) => void;
}

export default function FormTextAreaField({
  name,
  control,
  rules,
  onValueChange,
  ...rest
}: FormTextAreaFieldProps) {
  return (
    <Controller
      name={name}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextAreaField
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
