'use client';

import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import { cn } from '@/lib/utils';

export const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  },
};

/** Mono index kicker + tight display heading — the shared auth header. */
export function AuthHeading({
  index,
  kicker,
  title,
  subtitle,
}: {
  index: string;
  kicker: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
}) {
  return (
    <motion.div className="mb-9" variants={fadeUp}>
      <div className="mb-5 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
        <span className="text-primary">{index}</span>
        <span className="h-px w-8 bg-border" />
        <span>{kicker}</span>
      </div>
      <h2
        className="text-[2.3rem] font-semibold leading-[1.04] tracking-[-0.03em]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {title}
      </h2>
      {subtitle && (
        <p className="mt-3 text-[14px] leading-relaxed text-muted-foreground">{subtitle}</p>
      )}
    </motion.div>
  );
}

/** Full-width primary CTA with a travelling arrow. */
export function AuthSubmit({
  children,
  loading,
  className,
}: {
  children: React.ReactNode;
  loading?: boolean;
  className?: string;
}) {
  return (
    <CustomButton
      type="primary"
      htmlType="submit"
      fullWidth
      loading={loading}
      className={cn('group h-11 text-[14px]', className)}
    >
      {children}
      <ArrowRight className="ml-1 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
    </CustomButton>
  );
}

const toneCode = {
  success: 'text-emerald-500',
  error: 'text-destructive',
  info: 'text-primary',
} as const;

/**
 * Editorial result screen (success / error / sent) — replaces the generic
 * colored-circle-icon pattern with the same mono-code + display-type system.
 */
export function AuthResult({
  tone = 'info',
  code,
  kicker,
  title,
  description,
  children,
}: {
  tone?: keyof typeof toneCode;
  code: string;
  kicker: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="mb-5 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.3em]">
        <span className={toneCode[tone]}>{code}</span>
        <span className="h-px w-8 bg-border" />
        <span className="text-muted-foreground">{kicker}</span>
      </div>
      <h2
        className="text-[2.1rem] font-semibold leading-[1.05] tracking-[-0.03em]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {title}
      </h2>
      {description && (
        <p className="mt-3 text-[14px] leading-relaxed text-muted-foreground">{description}</p>
      )}
      {children && <div className="mt-7">{children}</div>}
    </motion.div>
  );
}
