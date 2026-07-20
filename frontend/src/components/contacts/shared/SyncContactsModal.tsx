'use client';

import { Download, FileUp } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { useCreateContactSync } from '@/lib/api/contactSyncs';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { useSchema, useSchemasList } from '@/lib/api/contactSchemas';
import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import type { SchemaField } from '@/types/contactSchema';
import { triggerCsvDownload } from '@/utils/download';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import AdvancedDirectoryConfig from './AdvancedDirectoryConfig';
import SyncErrorTable from './SyncErrorTable';
import SyncStatusChip from './SyncStatusChip';
import { useSyncStatusPolling } from './useSyncStatusPolling';

/**
 * The contact-sync stepper: pick datasource → mapping schema → (for CSV) upload file →
 * confirm → progress (polled).
 *
 * WHAT: creates a `ContactSync` for a directory from an uploaded CSV mapped through a
 * chosen org schema, then polls the sync to a terminal status showing live counts and,
 * on partial success, a completed-with-warnings banner linking the error report. If an
 * `agentId` is passed, it is sent so the worker auto-assigns imported contacts to that
 * agent on completion.
 *
 * WHEN: reuse for both the directory General view (no `agentId`) and the Agent Contacts
 * tab's "Sync + auto-assign" option (`agentId` set). This is the single sync-launch UI.
 */
export interface SyncContactsModalProps {
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
   * Called when a sync finishes so the parent can refresh its contacts list. Receives the
   * finished sync's id (optional) so the parent can poll/link it directly instead of
   * re-deriving it from a possibly-stale "most recent sync" query.
   */
  onCompleted?: (syncId?: string) => void;
}

/** Datasource types a sync can pull from. CSV is the only type at launch; the picker
 * is future-proofed for REST/others (which would swap the CSV upload for their own
 * config). Only `csv` reveals the file-upload control. */
const DATASOURCE_OPTIONS = [{ value: 'csv', label: 'CSV file' }];

/** Standard dial columns the CSV importer recognizes, always present in the template. */
const BASE_CSV_COLUMNS = ['name', 'phone_number'];

/**
 * Build a sample CSV template from a schema's fields so the user uploads a file whose
 * headers already match the mapping. Headers = the base dial columns + each field's
 * external `source_key` (or `field_name` when it maps by identity); one example row
 * illustrates the expected shape.
 */
function buildSampleCsv(schemaName: string, fields: SchemaField[]): string {
  // Each column carries its base (unmarked) key + the header text shown in the file.
  // Mandatory schema fields are marked with a trailing `*` so the user can see which
  // columns are required; the importer strips that `*` when mapping, so a filled-in
  // template still imports correctly.
  const columns: { key: string; header: string }[] = BASE_CSV_COLUMNS.map((key) => ({
    key,
    header: key,
  }));
  const seen = new Set(columns.map((c) => c.key));
  for (const f of fields) {
    const key = (f.source_key || f.field_name || '').trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    columns.push({ key, header: f.is_mandatory ? `${key}*` : key });
  }
  const exampleRow = columns.map((c) => {
    if (c.key === 'name') return 'John Doe';
    if (c.key === 'phone_number') return '+14155550123';
    return '';
  });
  const headerLine = columns.map((c) => c.header).join(',');
  return `${headerLine}\n${exampleRow.join(',')}\n`;
}

export default function SyncContactsModal({
  open,
  onClose,
  directoryId,
  agentId,
  defaultSchemaId,
  onCompleted,
}: SyncContactsModalProps) {
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

  const [datasourceType, setDatasourceType] = useState<string>('csv');
  const [schemaId, setSchemaId] = useState<string>(defaultSchemaId ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [syncId, setSyncId] = useState<string | null>(null);
  const [pickedDirectoryId, setPickedDirectoryId] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // The directory we actually import into: the fixed prop, or the user's pick (defaulting
  // to "Global" in the agent context).
  const effectiveDirectoryId = directoryId ?? pickedDirectoryId;

  // The selected schema's fields drive the downloadable sample template.
  const { data: schemaDetail } = useSchema(schemaId || null);

  const poll = useSyncStatusPolling(syncId);
  const notifiedSyncId = useRef<string | null>(null);

  const schemaOptions = (schemasPage?.data ?? []).map((s) => ({ value: s.id, label: s.name }));
  const isCsv = datasourceType === 'csv';

  // Notify the parent exactly once per sync, when it first reaches a terminal state, so
  // it can refetch its contacts list (a render-time call would loop).
  useEffect(() => {
    if (poll.isTerminal && syncId && notifiedSyncId.current !== syncId) {
      notifiedSyncId.current = syncId;
      onCompleted?.(syncId);
    }
  }, [poll.isTerminal, syncId, onCompleted]);

  // Agent context: default the target to the "Global" directory once the list arrives, if
  // the user hasn't overridden it. If no "Global" exists, the pick stays empty and the user
  // expands Advanced configuration to choose a directory.
  useEffect(() => {
    if (open && isAgentContext && !pickedDirectoryId && globalDirectory) {
      setPickedDirectoryId(globalDirectory.id);
    }
  }, [open, isAgentContext, pickedDirectoryId, globalDirectory]);

  const reset = () => {
    setDatasourceType('csv');
    setSchemaId(defaultSchemaId ?? '');
    setFile(null);
    setSyncId(null);
    notifiedSyncId.current = null;
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleDownloadSample = () => {
    if (!schemaDetail) return;
    const slug = (schemaDetail.name || 'schema').trim().replace(/\s+/g, '-').toLowerCase();
    triggerCsvDownload(
      `sample-${slug}.csv`,
      buildSampleCsv(schemaDetail.name, schemaDetail.fields ?? []),
    );
  };

  const startSync = async () => {
    if (!effectiveDirectoryId || !schemaId || (isCsv && !file)) {
      showToast.error('Pick a directory, a schema and a CSV file first.');
      return;
    }
    try {
      const sync = await createSync.mutateAsync({
        directory_id: effectiveDirectoryId,
        schema_id: schemaId,
        agent_id: agentId ?? undefined,
        file: file as File,
      });
      setSyncId(sync.id);
    } catch (err) {
      handleApiError(err);
    }
  };

  const counts = poll.sync?.counts ?? {};
  const canStart = !!effectiveDirectoryId && !!schemaId && (!isCsv || !!file);
  const rowErrors = poll.sync?.row_errors ?? [];

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Sync Contacts"
      hideFooter
      width="sm:max-w-lg"
    >
      <div className="flex flex-col gap-4">
        {!syncId && (
          <>
            <SelectInput
              name="sync-datasource"
              label="Datasource"
              options={DATASOURCE_OPTIONS}
              value={datasourceType}
              onValueChange={setDatasourceType}
              placeholder="Select a datasource"
            />

            <SelectInput
              name="sync-schema"
              label="Mapping schema"
              options={schemaOptions}
              value={schemaId}
              onValueChange={setSchemaId}
              placeholder="Select a schema"
            />

            {isCsv && (
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">CSV file</span>
                  {schemaId && (
                    <CustomButton
                      type="text"
                      size="xs"
                      icon={<Download className="size-3.5" />}
                      onClick={handleDownloadSample}
                    >
                      Download sample
                    </CustomButton>
                  )}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <div className="flex items-center gap-3 rounded-lg border border-input bg-background px-3 py-2">
                  <CustomButton
                    type="default"
                    size="sm"
                    icon={<FileUp className="size-4" />}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Choose file
                  </CustomButton>
                  <span
                    className={`min-w-0 flex-1 truncate text-sm ${
                      file ? 'text-foreground' : 'text-muted-foreground'
                    }`}
                    title={file?.name}
                  >
                    {file?.name ?? 'No file chosen'}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {schemaId
                    ? 'Upload a CSV whose columns match the selected schema, or download the sample above. Columns marked * are required.'
                    : 'Select a mapping schema to download a matching sample template.'}
                </p>
              </div>
            )}

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
                onClick={startSync}
                loading={createSync.isPending}
                disabled={!canStart}
              >
                Start sync
              </CustomButton>
            </div>
          </>
        )}

        {syncId && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Import status</span>
              {poll.status && <SyncStatusChip status={poll.status} />}
            </div>

            {poll.isTerminal && (
              <dl className="grid grid-cols-4 gap-2 text-center text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">Created</dt>
                  <dd className="font-medium">{counts.created ?? 0}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Updated</dt>
                  <dd className="font-medium">{counts.updated ?? 0}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Skipped</dt>
                  <dd className="font-medium">{counts.skipped ?? 0}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Failed</dt>
                  <dd className="font-medium">{counts.failed ?? 0}</dd>
                </div>
              </dl>
            )}

            {poll.completedWithWarnings && (
              <div
                role="alert"
                className="rounded-lg bg-orange-50 px-3 py-2 text-sm text-orange-800 ring-1 ring-inset ring-orange-200"
              >
                Import finished with some skipped rows — review them below.
              </div>
            )}

            {poll.isFailed && (
              <div
                role="alert"
                className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-inset ring-red-200"
              >
                {poll.sync?.error ?? 'The import failed. Please check the file and try again.'}
              </div>
            )}

            {poll.isTerminal && (
              <SyncErrorTable rowErrors={rowErrors} syncId={syncId ?? undefined} />
            )}

            <div className="flex justify-end gap-2 pt-2">
              {poll.isFailed && (
                <CustomButton type="default" onClick={reset}>
                  Retry
                </CustomButton>
              )}
              <CustomButton type="primary" onClick={handleClose} disabled={poll.isPolling}>
                {poll.isTerminal ? 'Done' : 'Importing…'}
              </CustomButton>
            </div>
          </div>
        )}
      </div>
    </CustomModal>
  );
}
