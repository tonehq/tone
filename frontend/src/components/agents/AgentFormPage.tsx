'use client';

import { useAtom } from 'jotai';
import {
  ArrowLeft,
  Bot,
  Cpu,
  FileCheck2,
  Loader2,
  MessageSquare,
  Phone,
  Save,
  Sparkles,
  Trash2,
  Volume2,
  Wrench,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';

import {
  createAgentAtom,
  deleteAgentAtom,
  fetchAgentAtom,
  updateAgentAtom,
} from '@/atoms/AgentsAtom';
import AiStep from '@/components/agents/agent-form/steps/AiStep';
import BasicsStep from '@/components/agents/agent-form/steps/BasicsStep';
import KnowledgePhoneStep from '@/components/agents/agent-form/steps/KnowledgePhoneStep';
import PromptStep from '@/components/agents/agent-form/steps/PromptStep';
import ReviewStep from '@/components/agents/agent-form/steps/ReviewStep';
import ToolsMcpStep from '@/components/agents/agent-form/steps/ToolsMcpStep';
import VoiceStep from '@/components/agents/agent-form/steps/VoiceStep';
import { AppLoader, CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { AgentDirection, AgentFormState } from '@/types/agent';
import {
  agentDetailToFormState,
  defaultFormState,
  formStateToCreatePayload,
  formStateToUpdatePayload,
} from '@/utils/agentFormUtils';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface AgentFormPageProps {
  agentType: AgentDirection;
  agentId?: string;
}

// The avatar chip and the direction badge both reuse this. In dark mode the
// 15% backgrounds disappear against the dark canvas, so we bump opacity and
// add a 1px inset ring for legibility on both themes.
const DIRECTION_STYLES: Record<AgentDirection, string> = {
  inbound:
    'bg-emerald-500/15 text-emerald-700 ring-1 ring-inset ring-emerald-500/20 dark:bg-emerald-500/25 dark:text-emerald-200 dark:ring-emerald-400/40',
  outbound:
    'bg-violet-500/15 text-violet-700 ring-1 ring-inset ring-violet-500/20 dark:bg-violet-500/25 dark:text-violet-200 dark:ring-violet-400/40',
  both: 'bg-sky-500/15 text-sky-700 ring-1 ring-inset ring-sky-500/20 dark:bg-sky-500/25 dark:text-sky-200 dark:ring-sky-400/40',
};

interface NavItem {
  key: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

const NAV_ITEMS: NavItem[] = [
  { key: 'basics', label: 'Basics', description: 'Identity & messages', icon: Bot },
  { key: 'prompt', label: 'Prompt', description: 'System prompt', icon: MessageSquare },
  { key: 'ai', label: 'AI', description: 'LLM provider & tuning', icon: Cpu },
  { key: 'voice', label: 'Voice', description: 'TTS & STT', icon: Volume2 },
  { key: 'tools', label: 'Tools & MCP', description: 'Callable functions', icon: Wrench },
  { key: 'knowledge', label: 'Knowledge & Phone', description: 'Docs & numbers', icon: Phone },
  { key: 'review', label: 'Review', description: 'Sanity check', icon: FileCheck2 },
];

export default function AgentFormPage({ agentType, agentId }: AgentFormPageProps) {
  const router = useRouter();
  const isEditMode = !!agentId;

  const [, fetchAgent] = useAtom(fetchAgentAtom);
  const [, createAgent] = useAtom(createAgentAtom);
  const [, updateAgent] = useAtom(updateAgentAtom);
  const [, deleteAgent] = useAtom(deleteAgentAtom);

  const [activeTab, setActiveTab] = useState<string>('basics');
  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [originalState, setOriginalState] = useState<AgentFormState | null>(null);

  const methods = useForm<AgentFormState>({
    defaultValues: defaultFormState(agentType),
    mode: 'onChange',
  });

  // ─── load on edit ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isEditMode || !agentId) return;
    let cancelled = false;
    setLoading(true);
    fetchAgent(agentId)
      .then((detail) => {
        if (cancelled) return;
        const hydrated = agentDetailToFormState(detail);
        methods.reset(hydrated);
        setOriginalState(hydrated);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, isEditMode]);

  // ─── save / delete ────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    const valid = await methods.trigger();
    if (!valid) {
      setActiveTab('basics');
      return;
    }
    const values = methods.getValues();
    setSaving(true);
    try {
      if (isEditMode && agentId && originalState) {
        const diff = formStateToUpdatePayload(values, originalState);
        if (Object.keys(diff).length === 0) {
          showToast.success('No changes', 'Nothing to update.');
          setSaving(false);
          return;
        }
        const updated = await updateAgent({ id: agentId, values: diff });
        const fresh = agentDetailToFormState(updated);
        methods.reset(fresh);
        setOriginalState(fresh);
        showToast.success('Agent updated');
      } else {
        const created = await createAgent(formStateToCreatePayload(values));
        showToast.success('Agent created');
        router.push(`/agents/edit/${created.agent_type}/${created.id}`);
      }
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  }, [agentId, createAgent, isEditMode, methods, originalState, router, updateAgent]);

  const handleConfirmDelete = useCallback(async () => {
    if (!agentId) return;
    setDeleting(true);
    try {
      await deleteAgent(agentId);
      router.push('/agents');
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  }, [agentId, deleteAgent, router]);

  // ─── derived ──────────────────────────────────────────────────────────────
  const agentName = methods.watch('name') || (isEditMode ? 'Untitled agent' : 'New agent');
  const agentInitial = (agentName.trim().charAt(0) || 'A').toUpperCase();

  const activeBody = useMemo(() => {
    switch (activeTab) {
      case 'basics':
        return <BasicsStep />;
      case 'prompt':
        return <PromptStep />;
      case 'ai':
        return <AiStep />;
      case 'voice':
        return <VoiceStep />;
      case 'tools':
        return <ToolsMcpStep />;
      case 'knowledge':
        return <KnowledgePhoneStep agentId={agentId ?? null} />;
      case 'review':
        return <ReviewStep onJump={(i) => setActiveTab(tabKeyForIndex(i))} />;
      default:
        return null;
    }
  }, [activeTab, agentId]);

  if (loading) {
    return <AppLoader className="h-full" />;
  }

  return (
    <FormProvider {...methods}>
      <div className="flex h-full min-h-0 flex-col bg-background">
        {/* ─── identity header (soft direction-tinted strip) ─────────────── */}
        <header
          className={cn(
            'relative flex shrink-0 items-center gap-3 overflow-hidden border-b border-border/60 px-5 py-3',
            // Subtle gradient washes the header in the direction's accent
            // colour without overwhelming the form below.
            agentType === 'inbound' &&
              'bg-gradient-to-r from-emerald-500/5 via-transparent to-transparent dark:from-emerald-500/10',
            agentType === 'outbound' &&
              'bg-gradient-to-r from-violet-500/5 via-transparent to-transparent dark:from-violet-500/10',
            agentType === 'both' &&
              'bg-gradient-to-r from-sky-500/5 via-transparent to-transparent dark:from-sky-500/10',
          )}
        >
          <CustomButton
            type="text"
            size="sm"
            icon={<ArrowLeft className="size-4" />}
            onClick={() => router.push('/agents')}
            className="-ml-2 h-8 text-muted-foreground hover:text-foreground"
            aria-label="Back to agents"
          />
          <div
            className={cn(
              'flex size-10 shrink-0 items-center justify-center rounded-xl text-base font-semibold shadow-sm',
              DIRECTION_STYLES[agentType],
            )}
            aria-hidden
          >
            {agentInitial}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="truncate font-display text-base font-semibold tracking-tight text-foreground">
                {agentName}
              </h1>
              <Badge
                className={cn(
                  'inline-flex shrink-0 items-center gap-1 px-1.5 py-0 text-[10px] capitalize',
                  DIRECTION_STYLES[agentType],
                )}
              >
                <Phone className="size-2.5" />
                {agentType}
              </Badge>
              {!isEditMode && (
                <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground">
                  <Sparkles className="size-3" />
                  New
                </span>
              )}
            </div>
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
              {isEditMode ? 'Editing agent configuration' : 'Set up a new voice agent'}
            </p>
          </div>
          {isEditMode && (
            <CustomButton
              type="text"
              size="sm"
              icon={<Trash2 className="size-4" />}
              onClick={() => setDeleteOpen(true)}
              className="h-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              Delete
            </CustomButton>
          )}
        </header>

        {/* ─── sidebar + content split ───────────────────────────────────── */}
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[220px_1fr]">
          {/* Sidebar nav */}
          <nav
            aria-label="Agent sections"
            className="hidden flex-col gap-0.5 border-r border-border/60 bg-muted/20 p-3 lg:flex"
          >
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = item.key === activeTab;
              return (
                <CustomButton
                  key={item.key}
                  type="text"
                  onClick={() => setActiveTab(item.key)}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'group flex h-auto w-full items-center justify-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors',
                    isActive
                      ? 'bg-foreground text-background hover:bg-foreground/90'
                      : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                  )}
                >
                  <Icon
                    className={cn(
                      'size-4 shrink-0',
                      isActive ? 'text-background' : 'text-muted-foreground',
                    )}
                    strokeWidth={2.25}
                  />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="text-[13px] font-medium leading-tight">{item.label}</span>
                    <span
                      className={cn(
                        'truncate text-[11px] leading-tight',
                        isActive ? 'text-background/70' : 'text-muted-foreground/80',
                      )}
                    >
                      {item.description}
                    </span>
                  </span>
                </CustomButton>
              );
            })}
          </nav>

          {/* Mobile fallback — horizontal scroll tab strip */}
          <nav
            aria-label="Agent sections (mobile)"
            className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-border/60 bg-background px-3 py-1.5 lg:hidden"
          >
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = item.key === activeTab;
              return (
                <CustomButton
                  key={item.key}
                  type="text"
                  size="sm"
                  onClick={() => setActiveTab(item.key)}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'shrink-0 gap-1.5 rounded-full px-3 text-[12px]',
                    isActive
                      ? 'bg-foreground text-background'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  <Icon className="size-3.5" />
                  {item.label}
                </CustomButton>
              );
            })}
          </nav>

          {/* Body */}
          <main className="min-h-0 overflow-auto px-5 py-5 lg:px-8 lg:py-6">
            <div className="mx-auto max-w-3xl">{activeBody}</div>
          </main>
        </div>

        {/* ─── sticky save bar ───────────────────────────────────────────── */}
        <footer className="sticky bottom-0 flex shrink-0 items-center justify-end gap-2 border-t border-border/60 bg-background/85 px-5 py-1.5 backdrop-blur">
          <CustomButton
            type="primary"
            size="sm"
            icon={
              saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />
            }
            onClick={handleSave}
            loading={saving}
          >
            {isEditMode ? 'Save changes' : 'Create agent'}
          </CustomButton>
        </footer>

        <CustomModal
          open={deleteOpen}
          onClose={() => setDeleteOpen(false)}
          title="Delete agent"
          description="This removes the agent and its configuration. Tools, MCP servers and uploads stay intact."
          confirmText="Delete"
          confirmType="danger"
          confirmLoading={deleting}
          onConfirm={handleConfirmDelete}
        />
      </div>
    </FormProvider>
  );
}

// Review step jumps still address sections by index (Basics=0, …) so this
// translation table keeps the public ReviewStep API unchanged.
const TAB_KEYS = ['basics', 'prompt', 'ai', 'voice', 'tools', 'knowledge', 'review'];
function tabKeyForIndex(i: number) {
  return TAB_KEYS[i] ?? TAB_KEYS[0];
}
