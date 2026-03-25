'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { cn } from '@/utils/cn';

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const isDark = resolvedTheme === 'dark';
  const hasLabel = className?.includes('justify-start');

  if (!mounted) {
    return (
      <button
        className={cn(
          'inline-flex size-9 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground',
          className,
        )}
        aria-label="Toggle theme"
      >
        <Sun className="size-4 shrink-0" />
        {hasLabel && <span>Light mode</span>}
      </button>
    );
  }

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className={cn(
        'inline-flex size-9 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
        className,
      )}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="size-4 shrink-0" /> : <Moon className="size-4 shrink-0" />}
      {hasLabel && <span>{isDark ? 'Light mode' : 'Dark mode'}</span>}
    </button>
  );
}
