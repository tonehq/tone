import { Check, Loader2, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { CustomButton, TextInput } from '@/components/shared';
import { cn } from '@/utils/cn';

/** Inline single-field editor for a folder name. Replaces the old
 * "rename folder" modal — clicking Rename on a folder card / breadcrumb
 * swaps the name span for this editor in place, so the user never leaves
 * the folders grid.
 *
 * ✓ (or Enter) commits, ✕ (or Escape) cancels. A blank / unchanged
 * value silently cancels — matches how contact-directory rename works
 * elsewhere in the app. The parent owns the mutation and passes
 * ``pending`` to disable the buttons + input while the save is in flight.
 *
 * Rendered inside interactive containers (a ``<button>`` card, a
 * clickable breadcrumb row), so click / keydown handlers stop propagation
 * to prevent the drill-in / focus-shift from also firing. */
export default function InlineFolderNameEditor({
  initialValue,
  onSave,
  onCancel,
  pending = false,
  size = 'sm',
}: {
  initialValue: string;
  onSave: (next: string) => void;
  onCancel: () => void;
  pending?: boolean;
  // ``sm`` = folder-card scale, ``md`` = breadcrumb scale. Tuned so the
  // editor visually replaces the corresponding name span without shifting
  // the surrounding layout.
  size?: 'sm' | 'md';
}) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    // Autofocus + select-all so the user can immediately overwrite or
    // start typing — matches native inline-rename UX (Finder, Drive).
    if (inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, []);

  useEffect(() => {
    // Re-sync when the underlying folder name changes externally
    // (concurrent rename by another user + a folders-query refetch).
    // Without this the editor keeps showing the stale name and ✓ would
    // try to rename a folder that no longer exists.
    setValue(initialValue);
  }, [initialValue]);

  const commit = () => {
    if (pending) return;
    const trimmed = value.trim();
    // Blank or unchanged → silent cancel (no toast, no request).
    if (!trimmed || trimmed === initialValue) {
      onCancel();
      return;
    }
    onSave(trimmed);
  };

  const handleContainerKeyDown = (e: React.KeyboardEvent) => {
    // Prevent the enclosing card / breadcrumb from picking up
    // Enter/Space when the input has focus.
    e.stopPropagation();
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
  };

  const handleSaveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    commit();
  };

  const handleCancelClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onCancel();
  };

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={handleContainerKeyDown}
      role="presentation"
    >
      <div className="min-w-0 flex-1">
        <TextInput
          ref={inputRef}
          name="folder-name"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleInputKeyDown}
          disabled={pending}
          maxLength={120}
          className={cn(
            'font-semibold text-foreground',
            size === 'sm' ? 'h-7 text-[13px]' : 'h-8 text-[14px]',
          )}
          aria-label="Folder name"
        />
      </div>
      <CustomButton
        type="text"
        size="icon-sm"
        onClick={handleSaveClick}
        disabled={pending}
        aria-label="Save folder name"
        title="Save"
        className={cn(
          'shrink-0 rounded-md text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-400',
          size === 'sm' ? 'size-7' : 'size-8',
        )}
      >
        {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
      </CustomButton>
      <CustomButton
        type="text"
        size="icon-sm"
        onClick={handleCancelClick}
        disabled={pending}
        aria-label="Cancel rename"
        title="Cancel"
        className={cn(
          'shrink-0 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground',
          size === 'sm' ? 'size-7' : 'size-8',
        )}
      >
        <X className="size-3.5" />
      </CustomButton>
    </div>
  );
}
