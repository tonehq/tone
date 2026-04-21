'use client';

import { cn } from '@/utils/cn';
import { Search } from 'lucide-react';
import React, { forwardRef } from 'react';

interface SearchBarProps extends Omit<React.ComponentProps<'input'>, 'type'> {
  containerClassName?: string;
}

const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(
  ({ placeholder = 'Search...', containerClassName, className, ...props }, ref) => (
    <div className={cn('relative max-w-sm', containerClassName)}>
      <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <input
        ref={ref}
        type="text"
        placeholder={placeholder}
        className={cn(
          'h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary',
          className,
        )}
        {...props}
      />
    </div>
  ),
);

SearchBar.displayName = 'SearchBar';

export default React.memo(SearchBar);
