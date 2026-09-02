interface SectionProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}

/** Titled card grouping a set of related fields on the integration form. */
export default function AppIntegrationSection({
  icon,
  title,
  description,
  children,
}: SectionProps) {
  return (
    <section className="space-y-4 rounded-lg border border-border bg-background p-4">
      <div>
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-[13px] font-semibold tracking-tight text-foreground">{title}</h2>
        </div>
        <p className="mt-0.5 text-[11.5px] text-muted-foreground">{description}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}
