'use client';

import { ChevronLeft } from 'lucide-react';

import { CustomButton } from '@/components/shared';

interface DrawerBackLinkProps {
  onClick: () => void;
  /** Usually the model name; falls back to a generic label. */
  label?: string;
}

// Breadcrumb-style "back" link rendered at the top of an edit drawer that was
// launched from the model detail drawer, so the user can return to that detail
// view instead of being stranded on the table.
export default function DrawerBackLink({ onClick, label }: DrawerBackLinkProps) {
  return (
    <CustomButton
      type="text"
      size="sm"
      onClick={onClick}
      icon={<ChevronLeft className="size-3.5" />}
      className="-ml-1 h-auto self-start px-1 py-0.5 text-muted-foreground hover:text-foreground"
    >
      {label ?? 'Back to details'}
    </CustomButton>
  );
}
