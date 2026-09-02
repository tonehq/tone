import { cn } from '@/utils/cn';

interface DetailRowProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  last?: boolean;
}

export default function DetailRow({ icon, label, value, last }: DetailRowProps) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-3', !last && 'border-b border-border/60')}>
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-[13px] text-muted-foreground">{label}</span>
      <span className="ml-auto truncate text-[13px] font-medium text-foreground">{value}</span>
    </div>
  );
}
