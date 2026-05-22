'use client';

import { motion } from 'framer-motion';
import React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

type AccentTone = 'primary' | 'amber' | 'emerald' | 'rose' | 'sky' | 'violet';

const ACCENT_BAR_CLASS: Record<AccentTone, string> = {
  primary: 'from-primary/80 via-primary to-primary/80',
  amber: 'from-amber-400 via-amber-500 to-amber-400',
  emerald: 'from-emerald-400 via-emerald-500 to-emerald-400',
  rose: 'from-rose-400 via-rose-500 to-rose-400',
  sky: 'from-sky-400 via-sky-500 to-sky-400',
  violet: 'from-violet-400 via-violet-500 to-violet-400',
};

export interface CustomCardProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  /** Top-right slot — usually an actions menu / button. */
  action?: React.ReactNode;
  children?: React.ReactNode;
  /** Bottom slot — usually metadata or a footer button row. */
  footer?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  headerClassName?: string;
  footerClassName?: string;
  centered?: boolean;
  /** Coloured stripe along the top edge. */
  accent?: AccentTone;
  /** Subtle hover lift + shadow. */
  interactive?: boolean;
  /** Entry animation index — used to stagger lists. */
  animationIndex?: number;
  onClick?: () => void;
}

export default function CustomCard({
  title,
  description,
  icon,
  action,
  children,
  footer,
  className,
  contentClassName,
  headerClassName,
  footerClassName,
  centered = false,
  accent,
  interactive = false,
  animationIndex,
  onClick,
}: CustomCardProps) {
  const hasHeader = !!(title || icon || action || description);

  const card = (
    <Card
      onClick={onClick}
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        interactive && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:border-border',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      {accent && (
        <span
          aria-hidden="true"
          className={cn(
            'absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r',
            ACCENT_BAR_CLASS[accent],
          )}
        />
      )}
      {hasHeader && (
        <CardHeader className={cn(centered && 'text-center', headerClassName)}>
          {action ? (
            <div className="flex items-start justify-between gap-3">
              <div className={cn('min-w-0', centered && 'text-center')}>
                {icon && <div className={cn('mb-2', centered && 'mx-auto w-fit')}>{icon}</div>}
                {title && (
                  <CardTitle className="text-base font-semibold tracking-tight">{title}</CardTitle>
                )}
                {description && (
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                    {description}
                  </p>
                )}
              </div>
              <div className="shrink-0">{action}</div>
            </div>
          ) : (
            <>
              {icon && <div className={cn('mb-2', centered && 'mx-auto w-fit')}>{icon}</div>}
              {title && (
                <CardTitle className="text-base font-semibold tracking-tight">{title}</CardTitle>
              )}
              {description && (
                <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                  {description}
                </p>
              )}
            </>
          )}
        </CardHeader>
      )}
      {children && <CardContent className={contentClassName}>{children}</CardContent>}
      {footer && (
        <div
          className={cn(
            'border-t border-border/60 bg-muted/30 px-5 py-3 text-[13px]',
            footerClassName,
          )}
        >
          {footer}
        </div>
      )}
    </Card>
  );

  if (animationIndex == null) return card;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.45,
        ease: [0.22, 1, 0.36, 1],
        delay: Math.min(animationIndex * 0.05, 0.4),
      }}
    >
      {card}
    </motion.div>
  );
}
