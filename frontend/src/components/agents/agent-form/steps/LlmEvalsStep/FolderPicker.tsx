import { useMemo } from 'react';

import { SelectInput, TextInput } from '@/components/shared';
import type { AgentLlmEvalFolder } from '@/types/agentLlmEval';

import { NEW_FOLDER_OPTION_VALUE } from './constants';

/** Shared folder picker for the create/edit and generate modals.
 *
 * Two states in one component: a dropdown of existing folders (with a
 * "+ Create new folder…" affordance) OR a text input when the user chose
 * to create a new one. Values are folder ids — when in create mode the
 * caller receives ``__new_folder__`` and the ``pendingName`` prop so it
 * can create-then-use the returned id at submit time. */
export default function FolderPicker({
  folders,
  value,
  onChange,
  newFolderName,
  onNewFolderNameChange,
  label = 'Folder',
}: {
  folders: AgentLlmEvalFolder[];
  // A folder id, or the sentinel ``NEW_FOLDER_OPTION_VALUE`` while the
  // user is typing a new-folder name.
  value: string;
  onChange: (v: string) => void;
  // New-folder text state — held on the parent so the submit handler can
  // read the typed name at commit time.
  newFolderName: string;
  onNewFolderNameChange: (name: string) => void;
  label?: string;
}) {
  const options = useMemo(
    () => [
      ...folders.map((f) => ({ value: f.id, label: f.name })),
      { value: NEW_FOLDER_OPTION_VALUE, label: '+ Create new folder…' },
    ],
    [folders],
  );

  const handleSelectChange = (v: string | null) => {
    if (!v) return;
    onChange(v);
  };

  const handlePickExistingInstead = () => {
    onChange(folders[0]?.id ?? '');
    onNewFolderNameChange('');
  };

  if (value === NEW_FOLDER_OPTION_VALUE) {
    return (
      <div className="flex flex-col gap-1">
        <TextInput
          name="folder_new"
          label={label}
          placeholder="New folder name"
          value={newFolderName}
          onChange={(e) => onNewFolderNameChange(e.target.value)}
        />
        <button
          type="button"
          className="self-start text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
          onClick={handlePickExistingInstead}
        >
          Pick an existing folder instead
        </button>
      </div>
    );
  }

  // ``value`` is passed through as-is (no ``|| folders[0]?.id`` fallback)
  // so the SelectInput's rendered value ALWAYS matches parent state — a
  // silent divergence would land scenarios in an unintended folder. The
  // parent's own useEffect backfills a valid id once folders load.
  return (
    <SelectInput
      name="folder_id"
      label={label}
      value={value}
      onValueChange={handleSelectChange}
      options={options}
    />
  );
}
