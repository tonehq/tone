'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { CustomButton } from '@/components/shared';

// Shared light/dark toggle used by the main app sidebar and the settings rail.
// `mounted` guards against a hydration mismatch while next-themes resolves.
export function ThemeToggleRow() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = mounted && resolvedTheme === 'dark';
  return (
    <CustomButton
      type="text"
      fullWidth
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      icon={
        isDark ? (
          <Sun className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Moon className="h-4 w-4 text-muted-foreground" />
        )
      }
      className="h-9 justify-start gap-3 px-3 font-normal"
    >
      {isDark ? 'Light mode' : 'Dark mode'}
    </CustomButton>
  );
}
