'use client';

import { cn } from '@/utils/cn';
import { Eye, EyeOff } from 'lucide-react';
import React, { forwardRef, useState } from 'react';
import { Controller } from 'react-hook-form';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import CustomButton from '@/components/shared/CustomButton';
import type { FormTextInputProps, TextInputBaseProps } from '@/types/components';

type TextInputProps = TextInputBaseProps | FormTextInputProps;

function isFormInput(props: TextInputProps): props is FormTextInputProps {
  return 'control' in props && props.control !== undefined;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const PlainTextInput = forwardRef<HTMLInputElement, TextInputBaseProps>(
  (
    {
      name,
      type = 'text',
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
      leftIcon,
      labelHint,
      ...props
    },
    ref,
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === 'password';

    if (loading) {
      return (
        <div className="mb-2">
          <Skeleton className="mb-1 h-4 w-20" />
          <Skeleton className="h-[42px] w-full" />
        </div>
      );
    }

    return (
      <div>
        {label && (
          <Label
            htmlFor={name}
            className={cn('mb-1.5 inline-flex items-center gap-1', labelClassName)}
          >
            {label}
            {labelHint}
            {isRequired && <span className="ml-0.5 text-destructive">*</span>}
          </Label>
        )}

        <div className="relative">
          {leftIcon && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground [&>svg]:size-4">
              {leftIcon}
            </span>
          )}
          <Input
            ref={ref}
            id={name}
            name={name}
            type={isPassword ? (showPassword ? 'text' : 'password') : type}
            placeholder={placeholder}
            value={value}
            defaultValue={defaultValue}
            onChange={onChange}
            disabled={disabled}
            aria-invalid={error || undefined}
            className={cn(
              error &&
                'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
              isPassword && 'pr-10',
              leftIcon && 'pl-9',
              className,
            )}
            {...props}
          />

          {isPassword && (
            <CustomButton
              type="text"
              htmlType="button"
              tabIndex={-1}
              aria-label="toggle password visibility"
              onClick={() => setShowPassword(!showPassword)}
              onMouseDown={(e) => e.preventDefault()}
              icon={!showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              className="absolute right-3 top-1/2 -translate-y-1/2 h-auto p-0 min-w-0 [&>span]:mr-0 text-muted-foreground hover:text-foreground focus:outline-none"
            />
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

PlainTextInput.displayName = 'PlainTextInput';

const MemoizedPlainTextInput = React.memo(PlainTextInput);

const TextInput = forwardRef<HTMLInputElement, TextInputProps>((props, ref) => {
  if (isFormInput(props)) {
    const { name, control, rules, onValueChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <MemoizedPlainTextInput
            {...rest}
            name={name}
            value={field.value ?? ''}
            onChange={(e) => {
              field.onChange(e.target.value);
              onValueChange?.(e.target.value);
            }}
            onBlur={field.onBlur}
            error={error ?? !!fieldState.error}
            helperText={fieldState.error?.message ?? helperText}
          />
        )}
      />
    );
  }

  return <MemoizedPlainTextInput ref={ref} {...props} />;
});

TextInput.displayName = 'TextInput';

export default React.memo(TextInput);
