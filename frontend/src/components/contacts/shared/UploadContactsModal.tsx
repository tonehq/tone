'use client';

import { useEffect, useState } from 'react';

import { useCreateContactSync } from '@/lib/api/contactSyncs';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { useSchema, useSchemasList } from '@/lib/api/contactSchemas';
import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import AdvancedDirectoryConfig from './AdvancedDirectoryConfig';
import ContactFileInput from './ContactFileInput';
import SampleDownloadMenu from './SampleDownloadMenu';
import SyncProgressPanel from './SyncProgressPanel';

/**
 * Upload Contacts — the local-file import flow: pick a mapping schema → upload a CSV or
 * `.xlsx` (agent context also exposes a target-directory override) → progress (polled).
 *
 * WHAT: creates a `ContactSync` for a directory from an uploaded file mapped through a
 * chosen org schema, then polls it to a terminal status via the shared
 * {@link SyncProgressPanel}. If an `agentId` is passed, the worker auto-assigns imported
 * contacts to that agent on completion. The upload uses the existing `POST /contact-syncs`
 * endpoint (no new API); the backend sniffs CSV vs `.xlsx` from the file's content.
 *
 * WHEN: this is the single Upload-launch UI — mounted on both the directory General view
 * (no `agentId`) and the Agent Contacts tab (`agentId` set). Third-party *sync* (as opposed
 * to local upload) is intentionally not offered here; that lives in the dormant
 * `SyncContactsModal`.
 */
export interface UploadContactsModalProps {
  open: boolean;
  onClose: () => void;
  /**
   * The directory to import into (directory General view). Omit in the agent-tab context —
   * the modal then defaults to the org's "Global" directory (resolved by name) and lets the
   * user override it via the Advanced configuration section.
   */
  directoryId?: string;
  /** Optional agent to auto-assign the imported contacts to (Agent Contacts tab). */
  agentId?: string | null;
  /** The directory's default schema id — preselected in the schema picker. */
  defaultSchemaId?: string | null;
  /**
   * Called when an upload finishes so the parent can refresh its contacts list. Receives the
   * finished sync's id (optional) so the parent can poll/link it directly instead of
   * re-deriving it from a possibly-stale "most recent sync" query.
   */
  onCompleted?: (syncId?: string) => void;
}

/** The `accept` hint for the OS file dialog: CSV + `.xlsx` (extensions + MIME types). */
const UPLOAD_ACCEPT =
  '.csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const UPLOAD_ALLOWED_EXTENSIONS = ['.csv', '.xlsx'];

export default function UploadContactsModal({
  open,
  onClose,
  directoryId,
  agentId,
  defaultSchemaId,
  onCompleted,
}: UploadContactsModalProps) {
  const { data: schemasPage } = useSchemasList({ page_size: 100 });
  const createSync = useCreateContactSync();

  // Agent-tab context: no fixed directory, but an agent to auto-assign to. Only then do we
  // need the directories list (to default to "Global" and offer the override).
  const isAgentContext = !directoryId && !!agentId;
  const directoriesQuery = useDirectoriesList({ page_size: 100 }, { enabled: isAgentContext });
  const directoryOptions = (directoriesQuery.data?.data ?? []).map((d) => ({
    value: d.id,
    label: d.name,
  }));
  // The org's seeded "Global" directory is the default target — resolved BY NAME from the
  // normal directories list (there is no /global endpoint).
  const globalDirectory = directoriesQuery.data?.data?.find((d) => d.name === 'Global');

  const [schemaId, setSchemaId] = useState<string>(defaultSchemaId ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [syncId, setSyncId] = useState<string | null>(null);
  const [pickedDirectoryId, setPickedDirectoryId] = useState<string>('');

  // The directory we actually import into: the fixed prop, or the user's pick (defaulting
  // to "Global" in the agent context).
  const effectiveDirectoryId = directoryId ?? pickedDirectoryId;

  // The selected schema's fields drive the downloadable sample template.
  const { data: schemaDetail } = useSchema(schemaId || null);

  const schemaOptions = (schemasPage?.data ?? []).map((s) => ({ value: s.id, label: s.name }));

  // Agent context: default the target to the "Global" directory once the list arrives, if
  // the user hasn't overridden it. If no "Global" exists, the pick stays empty and the user
  // expands Advanced configuration to choose a directory.
  useEffect(() => {
    if (open && isAgentContext && !pickedDirectoryId && globalDirectory) {
      setPickedDirectoryId(globalDirectory.id);
    }
  }, [open, isAgentContext, pickedDirectoryId, globalDirectory]);

  const reset = () => {
    setSchemaId(defaultSchemaId ?? '');
    setFile(null);
    setSyncId(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const startUpload = async () => {
    if (!effectiveDirectoryId || !schemaId || !file) {
      showToast.error('Pick a directory, a schema and a file first.');
      return;
    }
    try {
      const sync = await createSync.mutateAsync({
        directory_id: effectiveDirectoryId,
        schema_id: schemaId,
        agent_id: agentId ?? undefined,
        file,
      });
      setSyncId(sync.id);
    } catch (err) {
      handleApiError(err);
    }
  };

  const canStart = !!effectiveDirectoryId && !!schemaId && !!file;

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Upload Contacts"
      hideFooter
      width="sm:max-w-lg"
    >
      <div className="flex flex-col gap-4">
        {!syncId && (
          <>
            <SelectInput
              name="upload-schema"
              label="Mapping schema"
              options={schemaOptions}
              value={schemaId}
              onValueChange={setSchemaId}
              placeholder="Select a schema"
            />

            <ContactFileInput
              label="Contact file"
              accept={UPLOAD_ACCEPT}
              allowedExtensions={UPLOAD_ALLOWED_EXTENSIONS}
              value={file}
              onChange={setFile}
              hint={
                schemaId
                  ? 'Upload a CSV or .xlsx whose columns match the selected schema, or download the sample above. Columns marked * are required.'
                  : 'Select a mapping schema to download a matching sample template.'
              }
              sampleSlot={
                schemaId && schemaDetail ? (
                  <SampleDownloadMenu schemaId={schemaId} schemaName={schemaDetail.name} />
                ) : undefined
              }
            />

            {isAgentContext && (
              <AdvancedDirectoryConfig
                options={directoryOptions}
                value={pickedDirectoryId}
                onChange={setPickedDirectoryId}
                loading={directoriesQuery.isLoading}
              />
            )}

            <div className="flex justify-end gap-2 pt-2">
              <CustomButton type="default" onClick={handleClose}>
                Cancel
              </CustomButton>
              <CustomButton
                type="primary"
                onClick={startUpload}
                loading={createSync.isPending}
                disabled={!canStart}
              >
                Upload
              </CustomButton>
            </div>
          </>
        )}

        {syncId && (
          <SyncProgressPanel
            syncId={syncId}
            onReset={reset}
            onDone={handleClose}
            onTerminal={(id) => onCompleted?.(id)}
          />
        )}
      </div>
    </CustomModal>
  );
}
