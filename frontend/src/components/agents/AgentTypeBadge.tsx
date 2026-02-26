import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { PhoneIncoming, PhoneOutgoing } from 'lucide-react';

const AGENT_TYPE_CONFIG = {
  inbound: {
    label: 'Inbound',
    icon: PhoneIncoming,
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
  outbound: {
    label: 'Outbound',
    icon: PhoneOutgoing,
    className: 'border-violet-200 bg-violet-50 text-violet-700',
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
    <Badge variant="outline" className={cn('px-2.5 py-1', config.className)}>
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  );
}
