'use client';

import { cn } from '@/utils/cn';
import React, { forwardRef } from 'react';
import { Controller } from 'react-hook-form';

import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { FormTextAreaFieldProps, TextAreaFieldBaseProps } from '@/types/components';

type TextAreaFieldProps = TextAreaFieldBaseProps | FormTextAreaFieldProps;

function isFormTextArea(props: TextAreaFieldProps): props is FormTextAreaFieldProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainTextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldBaseProps>(
  (
    {
      name,
      label,
      placeholder,
      value,
      defaultValue,
      onChange,
      isRequired = false,
      loading = false,
      disabled = false,
      error = false,
      helperText,
      className,
      labelClassName,
      rows = 3,
      autoResize = false,
      ...props
    },
    ref,
  ) => {
    if (loading) {
      return (
        <div className="mb-2">
          {label && <Skeleton className="mb-1 h-4 w-20" />}
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    return (
      <div>
        {label && (
          <Label htmlFor={name} className={cn('mb-1.5', labelClassName)}>
            {label}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}

        <Textarea
          ref={ref}
          id={name}
          name={name}
          placeholder={placeholder}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          disabled={disabled}
          rows={rows}
          aria-invalid={error || undefined}
          className={cn(
            autoResize ? 'resize-y' : 'resize-none',
            error &&
              'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
            className,
          )}
          {...props}
        />

        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

PlainTextAreaField.displayName = 'PlainTextAreaField';

const MemoizedPlainTextAreaField = React.memo(PlainTextAreaField);

const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>((props, ref) => {
  if (isFormTextArea(props)) {
    const { name, control, rules, onValueChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <MemoizedPlainTextAreaField
            {...rest}
            name={name}
            value={field.value ?? ''}
            onChange={(e) => {
              field.onChange(e.target.value);
              onValueChange?.(e.target.value);
            }}
            onBlur={field.onBlur}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <MemoizedPlainTextAreaField ref={ref} {...props} />;
});

TextAreaField.displayName = 'TextAreaField';

export default React.memo(TextAreaField);
