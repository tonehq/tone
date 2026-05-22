'use client';

import { Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface PageLoaderProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  fullPage?: boolean;
}

const sizeMap = {
  sm: 'h-6 w-6',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
};

export default function PageLoader({
  message = 'Loading...',
  size = 'lg',
  className,
  fullPage = false,
}: PageLoaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        fullPage && 'min-h-screen',
        !fullPage && 'py-12',
        className,
      )}
    >
      <Loader2 className={cn('animate-spin text-primary mb-3', sizeMap[size])} />
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
