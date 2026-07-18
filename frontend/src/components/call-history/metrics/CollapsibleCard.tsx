'use client';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';
import { ChevronDown, ChevronRight } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import { useMetricsCollapse } from './MetricsCollapseContext';

interface CollapsibleCardProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Right-side controls (view toggle, sort, sample-count etc.). Hidden while collapsed. */
  actions?: React.ReactNode;
  /** Whether the card starts collapsed (default: false). */
  defaultCollapsed?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * Bordered card with a title row and a chevron toggle. When collapsed only
 * the title / subtitle and chevron remain — actions and body are hidden.
 *
 * Subscribes to [[MetricsCollapseContext]] so the page-level "Expand all" /
 * "Collapse all" buttons flip every card at once. Local toggle still works
 * between global bumps.
 */
export function CollapsibleCard({
  title,
  subtitle,
  actions,
  defaultCollapsed = false,
  children,
  className,
}: CollapsibleCardProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const { expandAllSignal, collapseAllSignal } = useMetricsCollapse();

  // Global "Expand all" fires — force open. Skip the initial mount so the
  // provider's starting signal (0) doesn't override `defaultCollapsed`.
  useEffect(() => {
    if (expandAllSignal === 0) return;
    setCollapsed(false);
  }, [expandAllSignal]);

  useEffect(() => {
    if (collapseAllSignal === 0) return;
    setCollapsed(true);
  }, [collapseAllSignal]);

  const Chevron = collapsed ? ChevronRight : ChevronDown;

  return (
    <div className={cn('rounded-lg border border-border p-3', className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          {typeof title === 'string' ? (
            <span className="text-sm font-medium text-foreground">{title}</span>
          ) : (
            title
          )}
          {subtitle &&
            (typeof subtitle === 'string' ? (
              <span className="ml-2 text-xs text-muted-foreground">{subtitle}</span>
            ) : (
              subtitle
            ))}
        </div>
        <div className="flex items-center gap-2">
          {!collapsed && actions}
          <CustomButton
            type="text"
            size="sm"
            onClick={() => setCollapsed((c) => !c)}
            aria-expanded={!collapsed}
            aria-label={collapsed ? 'Expand section' : 'Collapse section'}
            className="h-7 w-7 items-center justify-center rounded p-0 text-muted-foreground hover:text-foreground"
          >
            <Chevron className="size-4" />
          </CustomButton>
        </div>
      </div>
      {!collapsed && <div className="mt-2">{children}</div>}
    </div>
  );
}
