'use client';

import { cn } from '@/utils/cn';
import { Loader2 } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';

// ── Types ────────────────────────────────────────────────────────────────────

interface CustomButtonProps extends Omit<React.ComponentProps<'button'>, 'type'> {
  children?: React.ReactNode;
  loading?: boolean;
  type?: 'primary' | 'default' | 'text' | 'link' | 'danger';
  htmlType?: 'button' | 'submit' | 'reset';
  icon?: React.ReactNode;
  fullWidth?: boolean;
  size?: 'default' | 'xs' | 'sm' | 'lg' | 'icon' | 'icon-xs' | 'icon-sm' | 'icon-lg';
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
      children,
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
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        icon && <span className="inline-flex shrink-0">{icon}</span>
      )}
      {children}
    </Button>
  ),
);

CustomButton.displayName = 'CustomButton';

export default CustomButton;
