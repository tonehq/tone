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

export function AuthHeading({
  title,
  subtitle,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
}) {
  return (
    <motion.div className="mb-9" variants={fadeUp}>
      <h2 className="font-display text-[2.15rem] font-semibold leading-[1.05] tracking-[-0.032em]">
        {title}
      </h2>
      <span className="mt-5 block h-px w-10 bg-primary" />
      {subtitle && (
        <p className="mt-5 text-[14px] leading-relaxed text-muted-foreground">{subtitle}</p>
      )}
    </motion.div>
  );
}

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

const toneRule = {
  success: 'bg-success',
  error: 'bg-destructive',
  info: 'bg-primary',
} as const;

export function AuthResult({
  tone = 'info',
  title,
  description,
  children,
}: {
  tone?: keyof typeof toneRule;
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
      <h2 className="font-display text-[2.05rem] font-semibold leading-[1.05] tracking-[-0.032em]">
        {title}
      </h2>
      <span className={cn('mt-5 block h-px w-10', toneRule[tone])} />
      {description && (
        <p className="mt-5 text-[14px] leading-relaxed text-muted-foreground">{description}</p>
      )}
      {children && <div className="mt-8">{children}</div>}
    </motion.div>
  );
}
