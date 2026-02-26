'use client';

import { cn } from '@/utils/cn';
import { Eye, EyeOff } from 'lucide-react';
import React, { forwardRef, useState } from 'react';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import CustomButton from '@/components/shared/CustomButton';

interface TextInputProps extends Omit<React.ComponentProps<'input'>, 'size'> {
  name: string;
  type?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  leftIcon?: React.ReactNode;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
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
      <>
        {label && (
          <Label htmlFor={name} className={cn('mb-1.5', labelClassName)}>
            {label}
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
              icon={showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              className="absolute right-3 top-1/2 -translate-y-1/2 h-auto p-0 min-w-0 [&>span]:mr-0 text-muted-foreground hover:text-foreground focus:outline-none"
            />
          )}
        </div>

        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
            {helperText}
          </p>
        )}
      </>
    );
  },
);

TextInput.displayName = 'TextInput';

export default React.memo(TextInput);
