'use client';

import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { type ReactNode, useId, useState } from 'react';

import { cn } from '@/utils/cn';

export interface CollapsibleSectionProps {
  title: string;
  description?: ReactNode | ((expanded: boolean) => ReactNode);
  icon?: ReactNode;
  defaultExpanded?: boolean;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  children: ReactNode;
  className?: string;
}

export default function CollapsibleSection({
  title,
  description,
  icon,
  defaultExpanded = false,
  expanded: expandedProp,
  onExpandedChange,
  children,
  className,
}: CollapsibleSectionProps) {
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);
  const isControlled = expandedProp !== undefined;
  const expanded = isControlled ? expandedProp : internalExpanded;
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  const toggle = () => {
    const next = !expanded;
    if (!isControlled) setInternalExpanded(next);
    onExpandedChange?.(next);
  };

  const resolvedDescription =
    typeof description === 'function' ? description(expanded) : description;

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border bg-card transition-colors duration-200',
        expanded ? 'border-primary/30 shadow-sm' : 'border-border',
        className,
      )}
    >
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={toggle}
        className={cn(
          'group flex w-full cursor-pointer items-center gap-3 px-3.5 py-3 text-left',
          'transition-colors hover:bg-muted/40',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        )}
      >
        {icon && (
          <span
            className={cn(
              'flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors duration-200',
              expanded
                ? 'bg-primary/10 text-primary'
                : 'bg-muted text-muted-foreground group-hover:text-foreground',
            )}
          >
            {icon}
          </span>
        )}

        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-foreground">{title}</span>
          {resolvedDescription != null && (
            <span className="block truncate text-xs text-muted-foreground">
              {resolvedDescription}
            </span>
          )}
        </span>

        <ChevronDown
          className={cn(
            'size-4 shrink-0 text-muted-foreground',
            'motion-safe:transition-transform motion-safe:duration-200',
            expanded && 'rotate-180 text-primary',
          )}
          aria-hidden
        />
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={panelId}
            key="panel"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-3.5 pb-3.5 pt-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
