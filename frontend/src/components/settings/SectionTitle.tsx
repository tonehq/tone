'use client';

interface SectionTitleProps {
  icon: React.ElementType;
  iconColor: string;
  title: string;
  count?: number;
}

export default function SectionTitle({ icon: Icon, iconColor, title, count }: SectionTitleProps) {
  return (
    <div className="mb-5 flex items-center gap-2.5">
      <Icon size={15} className={iconColor} />
      <h2 className="text-[14px] font-semibold tracking-tight text-foreground">{title}</h2>
      {count != null && count > 0 && (
        <span className="inline-flex size-5 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground dark:bg-white/[0.06]">
          {count}
        </span>
      )}
      <div className="ml-2 h-px flex-1 bg-border/50 dark:bg-border/30" />
    </div>
  );
}
