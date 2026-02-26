'use client';

import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';

// ── Types ────────────────────────────────────────────────────────────────────

interface CustomButtonProps extends Omit<React.ComponentProps<'button'>, 'type'> {
  text: string;
  loading?: boolean;
  type?: 'primary' | 'default' | 'text' | 'link' | 'danger';
  htmlType?: 'button' | 'submit' | 'reset';
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

// ── Variant mapping ──────────────────────────────────────────────────────────
// Maps CustomButton `type` prop to shadcn Button `variant` prop.

const variantMap = {
  primary: 'default',
  default: 'outline',
  text: 'ghost',
  link: 'link',
  danger: 'destructive',
} as const;

// ── Component ────────────────────────────────────────────────────────────────

const CustomButton = React.forwardRef<HTMLButtonElement, CustomButtonProps>(
  (
    {
      text,
      loading = false,
      type = 'default',
      htmlType = 'button',
      onClick,
      disabled = false,
      icon,
      fullWidth = false,
      className,
      ...props
    },
    ref,
  ) => (
    <Button
      ref={ref}
      type={htmlType}
      variant={variantMap[type]}
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(fullWidth && 'w-full', className)}
      {...props}
    >
      {loading ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        icon && <span className="mr-2 inline-flex shrink-0">{icon}</span>
      )}
      {loading ? 'Loading...' : text}
    </Button>
  ),
);

CustomButton.displayName = 'CustomButton';

export { CustomButton };
export default CustomButton;
