'use client';

import { PageHeader } from '@/components/layout/page-header';
import { CustomButton } from '@/components/shared';
import { TOOL_TYPE_HEADER } from '@/constants/toolForm';
import { useGoBack } from '@/hooks/useGoBack';
import { getTemplateTools } from '@/services/toolService';
import type { Tool } from '@/types/tool';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowUpRight, Code2, Wrench } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const } },
};

export default function ToolCreatePage() {
  const router = useRouter();
  const goBack = useGoBack('/tools');

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
    router.push(`/tools/create/custom?template_id=${template.id}`);
  };

  return (
    <div className="space-y-10">
      <PageHeader
        index="01"
        kicker="New tool"
        title="Add a tool."
        description="Choose a built-in tool or create a custom API integration for your agents."
        actions={
          <CustomButton type="default" className="group h-10 text-[13px]" onClick={goBack}>
            <ArrowLeft className="h-4 w-4" />
            Back
          </CustomButton>
        }
      />

      <div className="space-y-4">
        <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <span className="text-primary">02</span>
          <span className="h-px w-8 bg-border" />
          <span>Choose a type</span>
        </div>

        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          {/* Custom tool */}
          <motion.div variants={item}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => router.push('/tools/create/custom')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  router.push('/tools/create/custom');
                }
              }}
              className="group relative h-full cursor-pointer overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition-colors group-hover:border-primary/40">
                  <Code2 className="h-5 w-5 text-foreground" strokeWidth={1.75} />
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
              </div>

              <div className="mt-4 flex items-center gap-2">
                <h3 className="text-[15px] font-semibold tracking-tight text-foreground">
                  Custom Tool
                </h3>
                <span className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  API
                </span>
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                Call any external API or webhook. Define the endpoint, parameters, and
                authentication.
              </p>

              <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
            </div>
          </motion.div>

          {loadingTemplates &&
            [1, 2].map((i) => (
              <motion.div key={`skeleton-${i}`} variants={item}>
                <div className="h-[148px] animate-pulse rounded-xl border border-border bg-card" />
              </motion.div>
            ))}

          {!loadingTemplates &&
            templates.map((template) => {
              const paramCount = Object.keys(template.parameters?.properties ?? {}).length;
              const headerConfig = TOOL_TYPE_HEADER[template.tool_type];
              const IconComponent = headerConfig?.icon ?? Wrench;
              const label = headerConfig?.label ?? 'Built-in';

              return (
                <motion.div key={template.uuid} variants={item}>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSelectTemplate(template)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSelectTemplate(template);
                      }
                    }}
                    className="group relative h-full cursor-pointer overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition-colors group-hover:border-primary/40">
                        <IconComponent className="h-5 w-5 text-foreground" strokeWidth={1.75} />
                      </div>
                      <ArrowUpRight className="h-4 w-4 text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
                    </div>

                    <div className="mt-4 flex items-center gap-2">
                      <h3 className="font-mono text-[15px] font-semibold tracking-tight text-foreground">
                        {template.name}
                      </h3>
                      <span className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                      {template.description}
                    </p>
                    {paramCount > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {Object.keys(template.parameters?.properties ?? {}).map((p) => (
                          <span
                            key={p}
                            className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                          >
                            {p}
                          </span>
                        ))}
                      </div>
                    )}

                    <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
                  </div>
                </motion.div>
              );
            })}
        </motion.div>
      </div>
    </div>
  );
}
