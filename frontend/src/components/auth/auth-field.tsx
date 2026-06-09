'use client';

import { useState } from 'react';
import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';
import { Eye, EyeOff } from 'lucide-react';

import { cn } from '@/lib/utils';

interface AuthFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  type?: 'text' | 'email' | 'password';
  autoComplete?: string;
  index?: string;
}

/**
 * AuthField — a bespoke, underline-style input for the auth surface.
 *
 * No box: a hairline baseline with a focus line that wipes in from the left,
 * a floating label driven by the CSS `:placeholder-shown` trick, and a quiet
 * monospace index in the corner. Deliberately unlike the app's boxed inputs.
 */
export function AuthField<T extends FieldValues>({
  name,
  control,
  label,
  type = 'text',
  autoComplete,
  index,
}: AuthFieldProps<T>) {
  const [reveal, setReveal] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (reveal ? 'text' : 'password') : type;

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error;
        return (
          <div className="group relative">
            <div className="relative pt-6">
              <input
                {...field}
                id={name}
                type={inputType}
                autoComplete={autoComplete}
                placeholder=" "
                aria-invalid={hasError || undefined}
                className={cn(
                  'peer w-full bg-transparent pb-2.5 pr-9 text-[15px] text-foreground caret-primary',
                  'outline-none placeholder:text-transparent',
                )}
              />

              {/* floating label */}
              <label
                htmlFor={name}
                className={cn(
                  'pointer-events-none absolute left-0 top-6 origin-left text-[15px] text-muted-foreground',
                  'transition-all duration-200 ease-out',
                  'peer-focus:top-0 peer-focus:text-[11px] peer-focus:font-medium peer-focus:uppercase peer-focus:tracking-[0.18em] peer-focus:text-primary',
                  'peer-[:not(:placeholder-shown)]:top-0 peer-[:not(:placeholder-shown)]:text-[11px] peer-[:not(:placeholder-shown)]:font-medium peer-[:not(:placeholder-shown)]:uppercase peer-[:not(:placeholder-shown)]:tracking-[0.18em]',
                  hasError && 'peer-focus:text-destructive',
                )}
              >
                {label}
              </label>

              {/* corner index */}
              {index && (
                <span className="absolute right-0 top-0 font-mono text-[10px] tracking-widest text-muted-foreground/40">
                  {index}
                </span>
              )}

              {/* password reveal */}
              {isPassword && (
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setReveal((r) => !r)}
                  onMouseDown={(e) => e.preventDefault()}
                  aria-label={reveal ? 'Hide password' : 'Show password'}
                  className="absolute bottom-2.5 right-0 text-muted-foreground/70 transition-colors hover:text-foreground"
                >
                  {reveal ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              )}

              {/* baseline */}
              <span
                className={cn(
                  'absolute bottom-0 left-0 h-px w-full',
                  hasError ? 'bg-destructive/60' : 'bg-border',
                )}
              />
              {/* focus line — wipes in from the left */}
              <span
                className={cn(
                  'absolute bottom-0 left-0 h-[1.5px] w-full origin-left scale-x-0 transition-transform duration-300 ease-out peer-focus:scale-x-100',
                  hasError ? 'bg-destructive' : 'bg-primary',
                )}
              />
            </div>

            {hasError && (
              <p className="mt-1.5 text-[12px] text-destructive">{fieldState.error?.message}</p>
            )}
          </div>
        );
      }}
    />
  );
}
