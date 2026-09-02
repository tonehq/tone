import { cn } from '@/utils/cn';
import { BADGE_TONES, type BadgeTone } from './appIntegrationConstants';

interface BadgeProps {
  tone: BadgeTone;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

/** Small status pill used on integration cards. */
export default function IntegrationBadge({ tone, icon, children }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
        BADGE_TONES[tone],
      )}
    >
      {icon}
      {children}
    </span>
  );
}
