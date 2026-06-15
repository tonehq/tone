'use client';

import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';

interface OrganizationCardMenuProps {
  orgId: string;
  role: string;
  onEdit: () => void;
  onDelete: () => void;
}

const OrganizationCardMenu: React.FC<OrganizationCardMenuProps> = ({
  orgId,
  role,
  onEdit,
  onDelete,
}) => {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [open]);

  return (
    <div className="relative">
      <CustomButton
        type="text"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((prev) => !prev);
        }}
        className="!h-auto size-8 rounded-lg p-0 text-muted-foreground opacity-0 transition-all hover:bg-muted hover:text-foreground group-hover:opacity-100"
        aria-label={`Actions for organization ${orgId}`}
        icon={<MoreHorizontal className="size-4" />}
      />

      {open && (
        <div className="absolute right-0 z-10 mt-1 w-40 overflow-hidden rounded-lg border border-border bg-popover shadow-lg">
          <CustomButton
            type="text"
            fullWidth
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onEdit();
            }}
            className="!h-auto !justify-start gap-2 rounded-none px-3 py-2 text-left text-sm font-normal text-foreground transition-colors hover:bg-muted"
            icon={<Pencil className="size-3.5" />}
          >
            Edit
          </CustomButton>
          {role === 'owner' && (
            <CustomButton
              type="text"
              fullWidth
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                onDelete();
              }}
              className="!h-auto !justify-start gap-2 rounded-none px-3 py-2 text-left text-sm font-normal text-destructive transition-colors hover:bg-destructive/10 hover:text-destructive"
              icon={<Trash2 className="size-3.5" />}
            >
              Delete
            </CustomButton>
          )}
        </div>
      )}
    </div>
  );
};

export default OrganizationCardMenu;
