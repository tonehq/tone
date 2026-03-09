'use client';

import React from 'react';
import { Controller, type Control, type RegisterOptions } from 'react-hook-form';

import CheckboxField from '@/components/shared/CheckboxField';

type CheckboxFieldProps = React.ComponentProps<typeof CheckboxField>;

export interface FormCheckboxFieldProps
  extends Omit<CheckboxFieldProps, 'checked' | 'onCheckedChange' | 'ref'> {
  control: Control<any>;
  rules?: RegisterOptions;
  onCheckedChange?: (checked: boolean) => void;
}

export default function FormCheckboxField({
  id,
  control,
  rules,
  onCheckedChange,
  ...rest
}: FormCheckboxFieldProps) {
  return (
    <Controller
      name={id}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <CheckboxField
          {...rest}
          id={id}
          checked={!!field.value}
          onCheckedChange={(checked) => {
            const boolVal = !!checked;
            field.onChange(boolVal);
            onCheckedChange?.(boolVal);
          }}
          error={rest.error ?? !!fieldState.error}
          helperText={rest.helperText ?? (fieldState.error?.message as string)}
        />
      )}
    />
  );
}
