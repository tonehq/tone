'use client';

import { CustomButton } from '@/components/shared';
import { TOOL_TYPE_HEADER } from '@/constants/toolForm';
import { getTemplateTools } from '@/services/toolService';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { ArrowLeft, Code2, Wrench } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function ToolCreatePage() {
  const router = useRouter();

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
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-background px-4 py-2">
        <div className="flex items-center gap-2">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={() => router.push('/tools')}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <span className="text-[13px] font-medium text-foreground">Create Tool</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
        <div className="mx-auto max-w-[600px] px-6 py-8">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-foreground">What type of tool?</h2>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Choose a built-in tool or create a custom API integration.
            </p>
          </div>

          <div className="mt-6 space-y-3">
            <div
              className="group flex cursor-pointer items-start gap-4 rounded-xl border border-border bg-background p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
              onClick={() => router.push('/tools/create/custom')}
            >
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Code2 size={20} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-[14px] font-semibold text-foreground">Custom Tool</h3>
                  <span className="rounded bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-500/10 dark:text-sky-400">
                    API
                  </span>
                </div>
                <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
                  Call any external API or webhook. Define the endpoint, parameters, and
                  authentication.
                </p>
              </div>
              <div className="flex shrink-0 items-center pt-1 text-muted-foreground transition-colors group-hover:text-foreground">
                <ArrowLeft size={14} className="rotate-180" />
              </div>
            </div>

            {loadingTemplates && (
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="h-[76px] animate-pulse rounded-xl bg-muted" />
                ))}
              </div>
            )}

            {!loadingTemplates &&
              templates.map((template) => {
                const paramCount = Object.keys(template.parameters?.properties ?? {}).length;
                const headerConfig = TOOL_TYPE_HEADER[template.tool_type];
                const IconComponent = headerConfig?.icon ?? Wrench;
                const iconBg = headerConfig?.bg ?? 'bg-amber-50 dark:bg-amber-500/10';
                const iconColor = headerConfig?.color ?? 'text-amber-700 dark:text-amber-400';

                return (
                  <div
                    key={template.uuid}
                    className="group flex cursor-pointer items-start gap-4 rounded-xl border border-border bg-background p-4 shadow-sm transition-all hover:border-primary/30 hover:shadow-md"
                    onClick={() => handleSelectTemplate(template)}
                  >
                    <div
                      className={cn(
                        'flex size-10 shrink-0 items-center justify-center rounded-lg',
                        iconBg,
                      )}
                    >
                      <IconComponent size={20} className={iconColor} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-mono text-[14px] font-semibold text-foreground">
                          {template.name}
                        </h3>
                        <span
                          className={cn(
                            'rounded px-1.5 py-0.5 text-[10px] font-medium',
                            iconBg,
                            iconColor,
                          )}
                        >
                          {headerConfig?.label ?? 'Built-in'}
                        </span>
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
                        {template.description}
                      </p>
                      {paramCount > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {Object.keys(template.parameters?.properties ?? {}).map((p) => (
                            <span
                              key={p}
                              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center pt-1 text-muted-foreground transition-colors group-hover:text-foreground">
                      <ArrowLeft size={14} className="rotate-180" />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}
