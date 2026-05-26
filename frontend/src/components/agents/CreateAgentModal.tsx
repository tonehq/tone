'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import { AgentType } from '@/types/agent';
import { cn } from '@/utils/cn';
import { ArrowDownLeft, ArrowUpRight, PhoneIncoming, PhoneOutgoing } from 'lucide-react';
import { useRouter } from 'next/navigation';

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

  const handleSelectAgent = (type: AgentType) => {
    onClose();
    if (type === 'inbound' || type === 'outbound') {
      router.push(`/agents/create/${type}`);
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
    </CustomModal>
  );
};

export default CreateAgentModal;
