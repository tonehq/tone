import type { ReactNode } from 'react';

interface DetailFieldProps {
  label: string;
  children: ReactNode;
}

const DetailField = ({ label, children }: DetailFieldProps) => (
  <div className="flex flex-col gap-1">
    <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
      {label}
    </span>
    <div className="text-sm text-foreground">{children}</div>
  </div>
);

export default DetailField;
