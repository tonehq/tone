import ProtocolDiagram from '@/components/mcp/form/ProtocolDiagram';
import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';
import { Check, Sparkles } from 'lucide-react';

export default function ProtocolCard({
  selected,
  onSelect,
  title,
  description,
  diagram,
  badge,
}: {
  selected: boolean;
  onSelect: () => void;
  title: string;
  description: string;
  diagram: 'shttp' | 'sse';
  badge?: string;
}) {
  return (
    <CustomButton
      type="text"
      onClick={onSelect}
      className={cn(
        '!h-auto !flex-col !items-stretch group relative flex flex-col gap-3 overflow-hidden rounded-lg border bg-background p-4 text-left transition-all',
        selected
          ? 'border-primary ring-2 ring-primary/25 shadow-sm'
          : 'border-border hover:border-primary/40 hover:bg-muted/20 hover:shadow-sm',
      )}
    >
      {selected && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-lg bg-gradient-to-br from-primary/[0.06] to-transparent"
        />
      )}

      <div className="relative flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-foreground">{title}</span>
          {badge && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9.5px] font-medium text-primary">
              <Sparkles size={9} />
              {badge}
            </span>
          )}
        </div>
        <span
          className={cn(
            'flex size-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
            selected ? 'border-primary bg-primary' : 'border-border bg-background',
          )}
        >
          {selected && <Check size={10} className="text-primary-foreground" strokeWidth={3} />}
        </span>
      </div>

      <ProtocolDiagram type={diagram} active={selected} />

      <p className="relative text-[12px] leading-relaxed text-muted-foreground">{description}</p>
    </CustomButton>
  );
}
