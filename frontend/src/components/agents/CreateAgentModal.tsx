'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import SearchableSelect from '@/components/shared/SearchableSelect';
import TextInput from '@/components/shared/TextInput';
import { createAgentFromTemplateAtom } from '@/atoms/AgentsAtom';
import { useAgentTemplates } from '@/lib/api/agentTemplates';
import { useQueryErrorToast } from '@/lib/api/useQueryErrorToast';
import { AgentType } from '@/types/agent';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { useSetAtom } from 'jotai';
import { ArrowDownLeft, ArrowUpRight, Check, PhoneIncoming, PhoneOutgoing } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

interface CreateAgentModalProps {
  open: boolean;
  onClose: () => void;
}

type Direction = 'outbound' | 'inbound';

interface AgentOption {
  type: Extract<AgentType, Direction>;
  title: string;
  tagline: string;
  description: string;
  icon: typeof PhoneIncoming;
  arrowIcon: typeof ArrowUpRight;
  /** Static (idle) gradient — flows in the call direction. */
  gradientClass: string;
  /** Brand surface tint for the icon container. */
  iconSurfaceClass: string;
  iconRingClass: string;
  iconColorClass: string;
  /** Pulse ring color behind the icon on hover. */
  pulseClass: string;
  /** Accent line color (bottom of card). */
  accentClass: string;
  /** Direction the accent fills on hover (origin side). */
  accentOriginClass: string;
  /** Soft inset glow on hover — no harsh borders. */
  hoverRingClass: string;
  /** Small caps tagline color. */
  taglineClass: string;
  arrowClass: string;
}

const agentOptions: AgentOption[] = [
  {
    type: 'outbound',
    title: 'Outbound',
    tagline: 'Initiates calls',
    description: 'Trigger calls from your workflows via Zapier, REST API, or HighLevel.',
    icon: PhoneOutgoing,
    arrowIcon: ArrowUpRight,
    gradientClass:
      'bg-[radial-gradient(120%_80%_at_0%_100%,theme(colors.violet.500/0.08),transparent_55%)]',
    iconSurfaceClass: 'bg-violet-500/10 dark:bg-violet-500/15',
    iconRingClass: 'ring-violet-500/20 dark:ring-violet-400/25',
    iconColorClass: 'text-violet-600 dark:text-violet-300',
    pulseClass: 'bg-violet-500/30 dark:bg-violet-400/30',
    accentClass: 'bg-violet-500 dark:bg-violet-400',
    accentOriginClass: 'origin-left',
    hoverRingClass:
      'group-hover:shadow-[0_0_0_1px_theme(colors.violet.500/0.25),0_18px_40px_-20px_theme(colors.violet.500/0.45)]',
    taglineClass: 'text-violet-600/80 dark:text-violet-300/80',
    arrowClass: 'text-violet-600 dark:text-violet-300',
  },
  {
    type: 'inbound',
    title: 'Inbound',
    tagline: 'Receives calls',
    description: 'Handle incoming calls routed by phone number, Zapier, or REST API.',
    icon: PhoneIncoming,
    arrowIcon: ArrowDownLeft,
    gradientClass:
      'bg-[radial-gradient(120%_80%_at_100%_100%,theme(colors.emerald.500/0.08),transparent_55%)]',
    iconSurfaceClass: 'bg-emerald-500/10 dark:bg-emerald-500/15',
    iconRingClass: 'ring-emerald-500/20 dark:ring-emerald-400/25',
    iconColorClass: 'text-emerald-600 dark:text-emerald-300',
    pulseClass: 'bg-emerald-500/30 dark:bg-emerald-400/30',
    accentClass: 'bg-emerald-500 dark:bg-emerald-400',
    accentOriginClass: 'origin-right',
    hoverRingClass:
      'group-hover:shadow-[0_0_0_1px_theme(colors.emerald.500/0.25),0_18px_40px_-20px_theme(colors.emerald.500/0.45)]',
    taglineClass: 'text-emerald-700/80 dark:text-emerald-300/80',
    arrowClass: 'text-emerald-600 dark:text-emerald-300',
  },
];

const CreateAgentModal: React.FC<CreateAgentModalProps> = ({ open, onClose }) => {
  const router = useRouter();
  const createFromTemplate = useSetAtom(createAgentFromTemplateAtom);

  // Templates are a read-only catalog, fetched only while the modal is open.
  const templatesQuery = useAgentTemplates({ enabled: open });
  const templates = useMemo(() => templatesQuery.data ?? [], [templatesQuery.data]);
  const sourcesLoading = templatesQuery.isLoading;
  useQueryErrorToast(templatesQuery.error);

  const [selected, setSelected] = useState('');
  const [name, setName] = useState('');
  // The name we pre-filled for the current selection. When the user leaves it
  // untouched we submit a blank name so the server applies its own default
  // (template name auto-suffixed on collision) instead of a verbatim name that
  // 409s on the second create from the same template.
  const [defaultName, setDefaultName] = useState('');
  const [creating, setCreating] = useState(false);

  // Reset the picker + name whenever the modal closes so the next open starts
  // clean. (Template data is fetched by the query above, gated on `open`.)
  useEffect(() => {
    if (!open) {
      setSelected('');
      setName('');
      setDefaultName('');
    }
  }, [open]);

  const sourceOptions = useMemo(
    () => templates.map((t) => ({ value: t.source_config_id, label: t.name })),
    [templates],
  );

  const handleSelectSource = (value: string) => {
    setSelected(value);
    const opt = sourceOptions.find((o) => o.value === value);
    if (!opt) return;
    // The template name is seeded verbatim; remember it so an unedited value can
    // be submitted blank and auto-named server-side on collision.
    const seeded = opt.label.slice(0, 50);
    setName(seeded);
    setDefaultName(seeded);
  };

  const handleSelectAgent = (type: AgentType) => {
    onClose();
    if (type === 'inbound' || type === 'outbound') {
      router.push(`/agents/create/${type}`);
    }
  };

  const handleCreateFromSource = async () => {
    const trimmed = name.trim();
    if (!selected || !trimmed || creating) return;
    // Unedited default → send blank so the server auto-names (and auto-numbers
    // on collision). Only a name the user actually customised is sent verbatim.
    const payloadName = trimmed === defaultName.trim() ? undefined : trimmed;
    setCreating(true);
    try {
      const created = await createFromTemplate({ sourceConfigId: selected, name: payloadName });
      onClose();
      router.push(`/agents/edit/${created.agent_type}/${created.id}/setup`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Choose type of agent"
      description="Pick how this agent should handle calls. You can build different agents for different flows."
      hideFooter
      width="sm:max-w-[640px]"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {agentOptions.map((option) => {
          const Icon = option.icon;
          const Arrow = option.arrowIcon;
          const isOutbound = option.type === 'outbound';
          return (
            <CustomButton
              key={option.type}
              type="text"
              onClick={() => handleSelectAgent(option.type)}
              className={cn(
                'group relative isolate flex h-auto cursor-pointer flex-col items-stretch justify-start gap-0 overflow-hidden rounded-2xl border border-border/70 bg-card p-5 text-left whitespace-normal',
                'shadow-[0_1px_0_0_theme(colors.border)] transition-all duration-300 ease-out',
                'hover:-translate-y-0.5 hover:border-transparent hover:bg-card',
                'focus-visible:outline-none focus-visible:-translate-y-0.5 focus-visible:border-transparent',
                option.hoverRingClass,
                'focus-visible:shadow-[0_0_0_2px_theme(colors.ring/0.6)]',
              )}
            >
              {/* Atmospheric gradient — flows in the call direction. */}
              <span
                aria-hidden
                className={cn(
                  'pointer-events-none absolute inset-0 -z-10 opacity-70 transition-opacity duration-500 group-hover:opacity-100',
                  option.gradientClass,
                )}
              />

              {/* Top row: icon (left) + corner arrow that lives in the natural direction. */}
              <div className="relative flex items-start justify-between gap-3">
                <div className="relative">
                  {/* Pulse ring — only on hover, suggests live activity. */}
                  <span
                    aria-hidden
                    className={cn(
                      'pointer-events-none absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100 motion-safe:group-hover:animate-ping',
                      option.pulseClass,
                    )}
                  />
                  <div
                    className={cn(
                      'relative flex size-11 items-center justify-center rounded-xl ring-1 ring-inset transition-transform duration-300 group-hover:scale-[1.04]',
                      option.iconSurfaceClass,
                      option.iconRingClass,
                    )}
                  >
                    <Icon className={cn('size-5', option.iconColorClass)} strokeWidth={2.25} />
                  </div>
                </div>

                <Arrow
                  className={cn(
                    'mt-1 size-4 opacity-0 transition-all duration-300 ease-out',
                    isOutbound
                      ? '-translate-x-1 translate-y-1 group-hover:translate-x-0 group-hover:translate-y-0'
                      : 'translate-x-1 -translate-y-1 group-hover:translate-x-0 group-hover:translate-y-0',
                    'group-hover:opacity-100',
                    option.arrowClass,
                  )}
                />
              </div>

              {/* Text block. */}
              <div className="relative mt-6 flex flex-col gap-1.5">
                <div className="flex items-baseline gap-2.5">
                  <p className="text-[15px] font-semibold tracking-tight text-foreground">
                    {option.title}
                  </p>
                  <span
                    className={cn(
                      'text-[10px] font-medium uppercase tracking-[0.12em]',
                      option.taglineClass,
                    )}
                  >
                    {option.tagline}
                  </span>
                </div>
                <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                  {option.description}
                </p>
              </div>

              {/* Directional accent bar — fills in the call direction on hover. */}
              <span
                aria-hidden
                className={cn(
                  'pointer-events-none absolute inset-x-5 bottom-0 h-px scale-x-0 transition-transform duration-500 ease-out group-hover:scale-x-100',
                  option.accentClass,
                  option.accentOriginClass,
                )}
              />
            </CustomButton>
          );
        })}
      </div>

      {/* Start from a template or an existing agent — copies the whole config
          into a new agent, then drops the user into the editor to tweak it. */}
      <div className="mt-6">
        <div className="mb-4 flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
            or start from a template
          </span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <div className="flex flex-col gap-3">
          <SearchableSelect
            name="create-agent-source"
            label="Template"
            options={sourceOptions}
            value={selected}
            onValueChange={handleSelectSource}
            loading={sourcesLoading}
            placeholder="Select a template to copy"
            searchPlaceholder="Search templates…"
            emptyMessage="No templates yet."
            renderOption={(option, isSelected) => (
              <div className="flex w-full items-center gap-2">
                <span className="rounded bg-violet-500/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-violet-600 dark:text-violet-300">
                  Template
                </span>
                <span className="flex-1 truncate">{option.label}</span>
                {isSelected && <Check className="ml-2 size-4 shrink-0" />}
              </div>
            )}
          />

          {selected && (
            <TextInput
              name="create-agent-clone-name"
              label="New agent name"
              value={name}
              maxLength={50}
              placeholder="e.g. Sales Concierge"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateFromSource()}
            />
          )}

          <CustomButton
            type="primary"
            fullWidth
            loading={creating}
            disabled={!selected || !name.trim()}
            onClick={handleCreateFromSource}
          >
            Create from selection
          </CustomButton>
        </div>
      </div>
    </CustomModal>
  );
};

export default CreateAgentModal;
