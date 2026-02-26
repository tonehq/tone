'use client';

import { cn } from '@/lib/utils';
import { Eye, EyeOff } from 'lucide-react';
import React, { forwardRef, useState } from 'react';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// ── Types ────────────────────────────────────────────────────────────────────

interface TextInputProps extends Omit<React.ComponentProps<'input'>, 'size'> {
  name: string;
  type?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded bg-gray-200', className)} {...props} />
);

// ── Component ────────────────────────────────────────────────────────────────

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
      fullWidth = true,
      className,
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
      <div className={cn('mb-2', !fullWidth && 'w-auto')}>
        {label && (
          <Label htmlFor={name} className="mb-1">
            {label}
            {isRequired && <span className="ml-0.5 text-red-500">*</span>}
          </Label>
        )}

        <div className="relative">
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
              error && 'border-red-500 focus-visible:border-red-500 focus-visible:ring-red-500/50',
              isPassword && 'pr-10',
              className,
            )}
            {...props}
          />

          {isPassword && (
            <button
              type="button"
              tabIndex={-1}
              aria-label="toggle password visibility"
              onClick={() => setShowPassword(!showPassword)}
              onMouseDown={(e) => e.preventDefault()}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-800 focus:outline-none"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          )}
        </div>

        {helperText && (
          <p className={cn('mt-1 text-xs', error ? 'text-red-500' : 'text-gray-500')}>
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

TextInput.displayName = 'TextInput';

export { TextInput };
export default TextInput;
