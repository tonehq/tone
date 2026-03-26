import React from 'react';

interface SectionHeaderProps {
  icon: React.ElementType;
  title: string;
}

export function SectionHeader({ icon: Icon, title }: SectionHeaderProps) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" />
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
    </div>
  );
}
