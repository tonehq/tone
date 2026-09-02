'use client';

import Image from 'next/image';

import { cn } from '@/lib/utils';

const LOCKUP = { w: 261, h: 104 };
const MARK = { w: 59, h: 104 };

const HEIGHTS = { sm: 18, md: 22, lg: 28 } as const;

interface LogoProps {
  className?: string;
  size?: keyof typeof HEIGHTS;
  showText?: boolean;
  inverted?: boolean;
}

export function Logo({ className, size = 'md', showText = true, inverted = false }: LogoProps) {
  const art = showText ? LOCKUP : MARK;
  const height = HEIGHTS[size];
  const width = Math.round((art.w / art.h) * height);
  const base = showText ? 'tone-logo' : 'tone-mark';

  const img = (variant: 'light' | 'dark', extra?: string) => (
    <Image
      src={`/brand/${base}${variant === 'dark' ? '-inverted' : ''}.png`}
      alt="Tone"
      width={width}
      height={height}
      priority
      className={cn('h-auto w-auto select-none', extra)}
      style={{ height, width }}
    />
  );

  if (inverted) {
    return <span className={cn('inline-flex items-center', className)}>{img('dark')}</span>;
  }

  return (
    <span className={cn('inline-flex items-center', className)}>
      {img('light', 'dark:hidden')}
      {img('dark', 'hidden dark:block')}
    </span>
  );
}

export function LogoIcon({
  className,
  size = 'lg',
}: {
  className?: string;
  size?: keyof typeof HEIGHTS;
}) {
  return <Logo showText={false} size={size} className={className} />;
}
