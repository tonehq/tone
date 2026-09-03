'use client';

import { Loader2, Radio } from 'lucide-react';

import { CustomTooltip } from '@/components/shared';
import { DropdownMenuItem } from '@/components/ui/dropdown-menu';

const MENU_ICON_CLASS = 'size-4';

interface PublishMenuItemProps {
  disabled: boolean;
  publishing: boolean;
  tooltip: string | null;
  onSelect: () => void;
}

/** Publish row in the agent-editor overflow menu. Kept in its own file so the
 *  disabled-tooltip branch stays local. Radix disabled menu items ignore
 *  pointer events, so we wrap in a tooltip trigger span to still surface the
 *  "no drafts" hint on hover. */
export default function PublishMenuItem({
  disabled,
  publishing,
  tooltip,
  onSelect,
}: PublishMenuItemProps) {
  const item = (
    <DropdownMenuItem disabled={disabled} onSelect={onSelect}>
      {publishing ? (
        <Loader2 className={`${MENU_ICON_CLASS} animate-spin`} />
      ) : (
        <Radio className={MENU_ICON_CLASS} />
      )}
      Publish
    </DropdownMenuItem>
  );
  if (!tooltip) return item;
  return (
    <CustomTooltip content={tooltip}>
      <span className="inline-flex w-full">{item}</span>
    </CustomTooltip>
  );
}
