import { Badge } from '@/components/ui/badge';
import { cn } from '@/utils/cn';
import { PhoneIncoming, PhoneOutgoing } from 'lucide-react';

const AGENT_TYPE_CONFIG = {
  inbound: {
    label: 'Inbound',
    icon: PhoneIncoming,
    className: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  },
  outbound: {
    label: 'Outbound',
    icon: PhoneOutgoing,
    className: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  },
} as const;

interface AgentTypeBadgeProps {
  agentType?: string;
}

export function AgentTypeBadge({ agentType }: AgentTypeBadgeProps) {
  const key = String(agentType).toLowerCase() === 'inbound' ? 'inbound' : 'outbound';
  const config = AGENT_TYPE_CONFIG[key];
  const Icon = config.icon;

  return (
    <Badge className={cn('px-2.5 py-1', config.className)}>
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}
