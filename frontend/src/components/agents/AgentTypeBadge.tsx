import { PhoneIncoming, PhoneOutgoing, Repeat2 } from 'lucide-react';

import type { IconChipTone } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { AgentDirection } from '@/types/agent';
import { cn } from '@/utils/cn';

export const DIRECTION_TONES: Record<AgentDirection, IconChipTone> = {
  inbound: 'emerald',
  outbound: 'primary',
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
      'bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300 dark:ring-emerald-400/30',
  },
  outbound: {
    label: 'Outbound',
    icon: PhoneOutgoing,
    className:
      'bg-teal-500/10 text-teal-700 ring-teal-500/25 dark:text-teal-300 dark:ring-teal-400/30',
  },
  both: {
    label: 'Both',
    icon: Repeat2,
    className: 'bg-sky-500/10 text-sky-700 ring-sky-500/25 dark:text-sky-300 dark:ring-sky-400/30',
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
        'border-transparent font-medium ring-1 ring-inset',
        SIZES[size],
        config.className,
        className,
      )}
    >
      <Icon strokeWidth={2.25} />
      {config.label}
    </Badge>
  );
}
