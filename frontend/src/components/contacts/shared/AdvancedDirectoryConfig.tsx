'use client';

import { SlidersHorizontal } from 'lucide-react';

import { CollapsibleSection, SelectInput } from '@/components/shared';
import type { SelectOption } from '@/types/components';

/**
 * The agent-context "Advanced configuration" panel: a directory override tucked behind the
 * shared {@link CollapsibleSection} disclosure.
 *
 * WHY: in the agent context the target directory defaults to the org's seeded "Global"
 * directory (resolved by name upstream), so the picker is hidden by default. Power users
 * expand it to send contacts to a different directory. The collapsed sub-line summarises the
 * current target so the choice stays legible without opening.
 *
 * Shared by BOTH the Add-contacts and Sync-contacts modals.
 */
export interface AdvancedDirectoryConfigProps {
  /** Selectable directories (id → name), typically from `useDirectoriesList`. */
  options: SelectOption[];
  /** The currently selected directory id. */
  value: string;
  /** Called with the new directory id when the user picks one. */
  onChange: (id: string) => void;
  /** Whether the directory list is still loading. */
  loading?: boolean;
}

export default function AdvancedDirectoryConfig({
  options,
  value,
  onChange,
  loading,
}: AdvancedDirectoryConfigProps) {
  const selectedLabel = options.find((o) => o.value === value)?.label;

  return (
    <CollapsibleSection
      title="Advanced configuration"
      icon={<SlidersHorizontal className="size-4" aria-hidden />}
      description={(expanded) =>
        expanded
          ? 'Choose which directory these contacts import into.'
          : selectedLabel
            ? `Target directory · ${selectedLabel}`
            : 'Set the target directory'
      }
    >
      <SelectInput
        name="advanced-directory"
        label="Directory"
        options={options}
        value={value}
        onValueChange={onChange}
        loading={loading}
        placeholder="Select a directory"
      />
      <p className="mt-1.5 text-xs text-muted-foreground">
        Contacts import into this directory. Defaults to your Global directory.
      </p>
    </CollapsibleSection>
  );
}
