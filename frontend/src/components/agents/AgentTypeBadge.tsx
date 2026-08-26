import { PhoneIncoming, PhoneOutgoing, Repeat2 } from 'lucide-react';

import type { IconChipTone } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { AgentDirection } from '@/types/agent';
import { cn } from '@/utils/cn';

export const DIRECTION_TONES: Record<AgentDirection, IconChipTone> = {
  inbound: 'emerald',
  outbound: 'violet',
  both: 'sky',
};

const DIRECTION_CONFIG: Record<
  AgentDirection,
  {
    label: string;
    icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
    className: string;
  }
> = {
  inbound: {
    label: 'Inbound',
    icon: PhoneIncoming,
    className:
      'from-emerald-500/25 via-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:from-emerald-400/25 dark:via-emerald-400/10 dark:text-emerald-200 dark:ring-emerald-400/30',
  },
  outbound: {
    label: 'Outbound',
    icon: PhoneOutgoing,
    className:
      'from-violet-500/25 via-violet-500/10 text-violet-700 ring-violet-500/25 dark:from-violet-400/25 dark:via-violet-400/10 dark:text-violet-200 dark:ring-violet-400/30',
  },
  both: {
    label: 'Both',
    icon: Repeat2,
    className:
      'from-sky-500/25 via-sky-500/10 text-sky-700 ring-sky-500/25 dark:from-sky-400/25 dark:via-sky-400/10 dark:text-sky-200 dark:ring-sky-400/30',
  },
};

const SIZES = {
  sm: 'gap-1 px-1.5 py-0 text-[10px] [&_svg]:size-2.5',
  md: 'gap-1.5 px-2.5 py-1 text-[11px] [&_svg]:size-3',
} as const;

export type AgentTypeBadgeSize = keyof typeof SIZES;

export function resolveDirection(agentType?: string): AgentDirection {
  const key = String(agentType).toLowerCase();
  return key === 'inbound' || key === 'both' ? (key as AgentDirection) : 'outbound';
}

interface AgentTypeBadgeProps {
  agentType?: string;
  size?: AgentTypeBadgeSize;
  className?: string;
}

export function AgentTypeBadge({ agentType, size = 'md', className }: AgentTypeBadgeProps) {
  const direction = resolveDirection(agentType);
  const config = DIRECTION_CONFIG[direction];
  const Icon = config.icon;

  return (
    <Badge
      className={cn(
        'relative isolate border-transparent bg-gradient-to-br to-transparent font-medium ring-1 ring-inset',
        SIZES[size],
        config.className,
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-b from-white/60 to-transparent opacity-70 dark:from-white/10 dark:opacity-50"
      />
      <Icon strokeWidth={2.25} />
      {config.label}
    </Badge>
  );
}
