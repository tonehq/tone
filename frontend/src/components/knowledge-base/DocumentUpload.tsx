'use client';

import { CloudUpload, Upload, X } from 'lucide-react';
import React, { useCallback, useMemo, useState } from 'react';

import { formatFileSize, getFileIcon } from '@/components/knowledge-base/knowledgeBaseHelpers';
import CustomButton from '@/components/shared/CustomButton';
import SelectInput from '@/components/shared/SelectInput';
import { useFileDropzone } from '@/hooks/useFileDropzone';
import { useIngestionConfigs } from '@/lib/api/ingestion-configs';
import { useUploadKnowledgeBase } from '@/lib/api/knowledge-base';
import type { AgentDropdownItem } from '@/types/agent';
import type { SelectOption } from '@/types/components';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

// Sentinel for the "no preset — use system defaults" option in the ingestion
// config dropdown. Distinct wording from NewIngestionRunModal's
// "Custom (one-off)" because upload has no per-field editor.
const DEFAULT_CONFIG_SENTINEL = '__default__';

interface DocumentUploadProps {
  agents: AgentDropdownItem[];
  agentsLoading: boolean;
  onUploadSuccess: () => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  agents,
  agentsLoading,
  onUploadSuccess,
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [ingestionConfigId, setIngestionConfigId] = useState<string>(DEFAULT_CONFIG_SENTINEL);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const uploadMutation = useUploadKnowledgeBase();

  // Same list params as NewIngestionRunModal so the two dropdowns stay in sync
  // and share TanStack Query's cache — do NOT introduce a second fetch hook.
  const { data: configsPage, isLoading: configsLoading } = useIngestionConfigs({
    page_no: 1,
    page_size: 200,
    is_active_only: true,
    sort_by: 'updated_at',
    sort_order: 'desc',
  });

  const agentOptions: SelectOption[] = agents
    .filter((a) => !!a.uuid)
    .map((a) => ({ label: a.name, value: a.uuid as string }));

  const configOptions: SelectOption[] = useMemo(
    () => [
      { value: DEFAULT_CONFIG_SENTINEL, label: 'Use default' },
      ...(configsPage?.data ?? []).map((c) => ({ value: c.id, label: c.name })),
    ],
    [configsPage],
  );

  // Validation lives in the hook; here we only dedupe (by name + size) against
  // already-queued files before appending.
  const addFiles = useCallback((incoming: File[]) => {
    setFiles((prev) => {
      const additions = incoming.filter(
        (f) => !prev.some((ef) => ef.name === f.name && ef.size === f.size),
      );
      return additions.length > 0 ? [...prev, ...additions] : prev;
    });
  }, []);

  const {
    isDragging,
    fileInputRef,
    acceptAttr,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleInputChange,
    openFilePicker,
  } = useFileDropzone({ onFiles: addFiles });

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const uploading = uploadMutation.isPending || progress != null;

  const handleUpload = async () => {
    // Agent is optional — a KB can be uploaded unassigned (backend accepts a
    // missing agent_id). Only the files are required.
    if (files.length === 0) return;
    const queue = files;
    const total = queue.length;
    const failed: File[] = [];
    let succeeded = 0;
    let lastError: unknown = null;

    const configForUpload =
      ingestionConfigId === DEFAULT_CONFIG_SENTINEL ? null : ingestionConfigId;

    setProgress({ done: 0, total });
    for (let i = 0; i < queue.length; i += 1) {
      try {
        await uploadMutation.mutateAsync({
          // Empty selection → null so no agent_id is sent (unassigned upload).
          agentId: selectedAgentId || null,
          file: queue[i],
          ingestionConfigId: configForUpload,
        });
        succeeded += 1;
      } catch (error) {
        failed.push(queue[i]);
        lastError = error;
      }
      setProgress({ done: i + 1, total });
    }
    setProgress(null);

    // Keep only the failed files so the user can retry them without re-uploading duplicates.
    setFiles(failed);

    if (failed.length === 0) {
      const label = total === 1 ? 'Document uploaded' : `${total} documents uploaded`;
      showToast.success(label, 'Your documents are now part of the knowledge base.');
      setSelectedAgentId('');
      setIngestionConfigId(DEFAULT_CONFIG_SENTINEL);
      onUploadSuccess();
    } else if (succeeded === 0) {
      handleApiError(lastError);
    } else {
      // Leave the modal open with the failed files still listed so the user
      // can retry them. The per-file mutation already invalidates the table.
      // Surface the backend `detail` when present (e.g. the 409 duplicate-
      // name message) so the user sees WHY the upload failed instead of a
      // generic "retry" prompt.
      const detail =
        typeof lastError === 'object' && lastError !== null
          ? ((lastError as { response?: { data?: { detail?: unknown } } }).response?.data
              ?.detail as string | undefined)
          : undefined;
      showToast.error(
        `${succeeded} of ${total} uploaded`,
        typeof detail === 'string' && detail
          ? detail
          : `${failed.length} failed — retry the remaining files.`,
      );
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-5 overflow-hidden">
      <SelectInput
        name="agent"
        label="Agent"
        placeholder={agentOptions.length === 0 ? 'No agents available' : 'Select an agent'}
        options={agentOptions}
        value={selectedAgentId}
        onValueChange={setSelectedAgentId}
        loading={agentsLoading}
        disabled={agentOptions.length === 0}
        helperText="Optional — leave empty to upload without assigning to an agent."
      />

      <SelectInput
        name="ingestion_config"
        label="Ingestion config"
        placeholder="Use default"
        options={configOptions}
        value={ingestionConfigId}
        onValueChange={setIngestionConfigId}
        loading={configsLoading}
        helperText="Optional — leave as default to use system defaults."
      />

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground">
          Documents <span className="text-destructive">*</span>
        </label>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={openFilePicker}
          className={cn(
            'relative flex min-h-[148px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed transition-all',
            isDragging
              ? 'scale-[1.01] border-primary bg-primary/10'
              : 'border-border hover:border-primary/50 hover:bg-accent/40',
          )}
        >
          <div className="flex flex-col items-center gap-3 px-6 py-7">
            <div
              className={cn(
                'flex h-12 w-12 items-center justify-center rounded-2xl transition-colors',
                isDragging ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary',
              )}
            >
              <CloudUpload className="size-6" />
            </div>
            <div className="text-center">
              <p className="text-sm text-foreground">
                Drag &amp; drop or{' '}
                <span className="font-medium text-primary underline-offset-2 hover:underline">
                  browse files
                </span>
              </p>
              <p className="mt-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                PDF · DOCX · TXT · CSV · JSON · max 100 MB each
              </p>
            </div>
          </div>
        </div>

        {files.length > 0 && (
          <div className="mt-3 space-y-2">
            {files.map((file, index) => (
              <div
                key={`${file.name}-${file.size}`}
                className="flex items-center gap-3 rounded-xl border border-border bg-muted/40 px-3.5 py-2.5"
              >
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-background ring-1 ring-border">
                  {getFileIcon(file.name)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                </div>
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={() => removeFile(index)}
                  className="shrink-0 text-muted-foreground hover:text-foreground"
                  aria-label={`Remove ${file.name}`}
                  icon={<X className="size-4" />}
                />
              </div>
            ))}
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptAttr}
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {progress && progress.total > 1 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Uploading {progress.done + (progress.done < progress.total ? 1 : 0)} of{' '}
              {progress.total}
            </span>
            <span className="tabular-nums">
              {Math.round((progress.done / progress.total) * 100)}%
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${(progress.done / progress.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      <CustomButton
        type="primary"
        fullWidth
        loading={uploading}
        disabled={files.length === 0}
        onClick={handleUpload}
        icon={<Upload className="size-4" />}
      >
        {files.length > 1 ? `Upload ${files.length} files` : 'Upload document'}
      </CustomButton>
    </div>
  );
};

export default DocumentUpload;
