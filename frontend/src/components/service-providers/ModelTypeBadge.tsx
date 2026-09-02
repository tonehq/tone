import { Badge } from '@/components/ui/badge';
import type { ServiceKind } from '@/types/service';
import { cn } from '@/utils/cn';

import { TYPE_BADGE_STYLES } from './constants';

interface ModelTypeBadgeProps {
  kind: ServiceKind;
}

const ModelTypeBadge = ({ kind }: ModelTypeBadgeProps) => (
  <Badge
    className={cn(
      'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
      TYPE_BADGE_STYLES[kind] ?? '',
    )}
  >
    {kind}
  </Badge>
);

export default ModelTypeBadge;
