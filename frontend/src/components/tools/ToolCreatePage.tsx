'use client';

import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { ArrowLeft, ArrowUpRight, Code2, Wrench } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { CustomButton } from '@/components/shared';
import { TOOL_TYPE_HEADER } from '@/constants/toolForm';
import { useGoBack } from '@/hooks/useGoBack';
import { getTemplateTools } from '@/services/toolService';
import type { Tool } from '@/types/tool';
import { readAttachContext, withAttachContext } from '@/utils/agentAttachmentContext';
import { cn } from '@/utils/cn';

interface ToolTypeCardProps {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  iconBg: string;
  iconColor: string;
  title: string;
  titleClassName?: string;
  badge?: string;
  badgeClassName?: string;
  description: string;
  chips?: string[];
  onClick: () => void;
  variants: Variants;
}

function ToolTypeCard({
  icon: Icon,
  iconBg,
  iconColor,
  title,
  titleClassName,
  badge,
  badgeClassName,
  description,
  chips,
  onClick,
  variants,
}: ToolTypeCardProps) {
  return (
    <motion.div variants={variants}>
      <CustomButton
        type="text"
        fullWidth
        onClick={onClick}
        className={cn(
          'group h-auto items-start justify-start gap-4 whitespace-normal rounded-2xl border border-border/70 bg-card p-5 text-left font-normal',
          'transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-primary/30 hover:bg-card',
          'hover:shadow-[0_10px_34px_-14px_hsl(var(--primary)/0.45)]',
          'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'motion-reduce:transition-none motion-reduce:hover:translate-y-0',
        )}
      >
        <span
          className={cn(
            'flex size-11 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset ring-border/50 transition-colors duration-200',
            iconBg,
          )}
        >
          <Icon className={cn('size-[22px]', iconColor)} strokeWidth={1.9} />
        </span>

        <span className="flex min-w-0 flex-1 flex-col">
          <span className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                'text-[15px] font-semibold tracking-tight text-foreground',
                titleClassName,
              )}
            >
              {title}
            </span>
            {badge && (
              <span
                className={cn(
                  'rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                  badgeClassName ?? 'bg-primary/10 text-primary',
                )}
              >
                {badge}
              </span>
            )}
          </span>
          <span className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            {description}
          </span>
          {chips && chips.length > 0 && (
            <span className="mt-2.5 flex flex-wrap gap-1">
              {chips.map((c) => (
                <span
                  key={c}
                  className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                >
                  {c}
                </span>
              ))}
            </span>
          )}
        </span>

        <ArrowUpRight className="size-4 shrink-0 text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
      </CustomButton>
    </motion.div>
  );
}

export default function ToolCreatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const goBack = useGoBack('/tools');
  const reduceMotion = useReducedMotion();

  // If we were opened from the agent config page ("New tool" button), forward
  // the attach context onto whichever /tools/create/custom URL the user picks
  // so the form page can finish the attach after save. See
  // ``utils/agentAttachmentContext.ts`` for the contract.
  const attachCtx = useMemo(() => readAttachContext(searchParams), [searchParams]);
  const customCreateHref = attachCtx
    ? withAttachContext('/tools/create/custom', attachCtx)
    : '/tools/create/custom';

  const [templates, setTemplates] = useState<Tool[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  useEffect(() => {
    setLoadingTemplates(true);
    getTemplateTools()
      .then(setTemplates)
      .catch(() => {
        setTemplates([]);
      })
      .finally(() => setLoadingTemplates(false));
  }, []);

  const handleSelectTemplate = (template: Tool) => {
    const base = `/tools/create/custom?template_id=${template.id}`;
    router.push(attachCtx ? withAttachContext(base, attachCtx) : base);
  };

  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduceMotion ? 0 : 0.05, delayChildren: 0.04 } },
  };
  const item: Variants = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 10 },
    show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] } },
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* ── Header (soft, borderless toolbar) ──────────────────── */}
      <header className="flex shrink-0 items-center gap-2 py-3">
        <CustomButton
          type="text"
          onClick={goBack}
          aria-label="Back to tools"
          className="size-8 rounded-lg p-0 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
        </CustomButton>
        <span className="text-sm font-medium text-foreground">Create Tool</span>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-2xl px-6 pb-14 pt-6 sm:pt-10">
          {/* Hero */}
          <div className="text-center">
            <div className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary/80">
              <span className="size-1.5 rounded-full bg-primary" />
              New tool
            </div>
            <h1 className="mt-3 text-[26px] font-semibold leading-tight tracking-tight text-foreground">
              What type of tool?
            </h1>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
              Choose a built-in tool or create a custom API integration your agent can call.
            </p>
          </div>

          {/* Options */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="mt-8 space-y-3"
          >
            <ToolTypeCard
              icon={Code2}
              iconBg="bg-primary/10 group-hover:bg-primary group-hover:ring-primary"
              iconColor="text-primary group-hover:text-primary-foreground"
              title="Custom Tool"
              badge="API"
              badgeClassName="bg-sky-500/10 text-sky-700 dark:text-sky-400"
              description="Call any external API or webhook. Define the endpoint, parameters, and authentication."
              onClick={() => router.push(customCreateHref)}
              variants={item}
            />

            {loadingTemplates &&
              [0, 1].map((i) => (
                <motion.div
                  key={i}
                  variants={item}
                  className="h-[92px] animate-pulse rounded-2xl border border-border/60 bg-muted/40"
                />
              ))}

            {!loadingTemplates &&
              templates.map((template) => {
                const chips = Object.keys(template.parameters?.properties ?? {});
                const headerConfig = TOOL_TYPE_HEADER[template.tool_type];
                return (
                  <ToolTypeCard
                    key={template.uuid}
                    icon={headerConfig?.icon ?? Wrench}
                    iconBg={headerConfig?.bg ?? 'bg-amber-500/10'}
                    iconColor={headerConfig?.color ?? 'text-amber-700 dark:text-amber-400'}
                    title={template.name}
                    titleClassName="font-mono"
                    badge={headerConfig?.label ?? 'Built-in'}
                    badgeClassName={cn(headerConfig?.bg, headerConfig?.color)}
                    description={template.description ?? ''}
                    chips={chips}
                    onClick={() => handleSelectTemplate(template)}
                    variants={item}
                  />
                );
              })}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
