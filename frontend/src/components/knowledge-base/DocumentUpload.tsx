'use client';

import { CloudUpload, File, FileCode, FileSpreadsheet, FileText, Upload, X } from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import SelectInput from '@/components/shared/SelectInput';
import { useUploadKnowledgeBase } from '@/lib/api/knowledge-base';
import type { AgentDropdownItem } from '@/types/agent';
import type { SelectOption } from '@/types/components';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'text/html',
  'application/json',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const ACCEPTED_EXTENSIONS = ['pdf', 'txt', 'csv', 'html', 'json', 'docx'];
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

interface DocumentUploadProps {
  agents: AgentDropdownItem[];
  agentsLoading: boolean;
  onUploadSuccess: () => void;
}

function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return <FileText className="size-5 text-red-500" />;
    case 'docx':
    case 'doc':
      return <FileText className="size-5 text-blue-500" />;
    case 'csv':
      return <FileSpreadsheet className="size-5 text-emerald-500" />;
    case 'json':
      return <FileCode className="size-5 text-amber-500" />;
    case 'txt':
      return <FileText className="size-5 text-gray-500" />;
    default:
      return <File className="size-5 text-muted-foreground" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  agents,
  agentsLoading,
  onUploadSuccess,
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useUploadKnowledgeBase();

  const agentOptions: SelectOption[] = agents
    .filter((a) => !!a.uuid)
    .map((a) => ({ label: a.name, value: a.uuid as string }));

  const validateFile = useCallback((f: File): boolean => {
    const ext = f.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      showToast.error(`Unsupported: ${f.name}`, `Supported: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      return false;
    }
    if (f.size > MAX_FILE_SIZE) {
      showToast.error(`Too large: ${f.name}`, 'Maximum file size is 100 MB');
      return false;
    }
    return true;
  }, []);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const validated: File[] = [];
      for (const f of Array.from(newFiles)) {
        const isDuplicate = files.some((ef) => ef.name === f.name && ef.size === f.size);
        if (isDuplicate) continue;
        if (validateFile(f)) validated.push(f);
      }
      if (validated.length > 0) setFiles((prev) => [...prev, ...validated]);
    },
    [validateFile, files],
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
      e.target.value = '';
    },
    [addFiles],
  );

  const uploading = uploadMutation.isPending || progress != null;

  const handleUpload = async () => {
    if (files.length === 0 || !selectedAgentId) return;
    const queue = files;
    const total = queue.length;
    const failed: File[] = [];
    let succeeded = 0;
    let lastError: unknown = null;

    setProgress({ done: 0, total });
    for (let i = 0; i < queue.length; i += 1) {
      try {
        await uploadMutation.mutateAsync({ agentId: selectedAgentId, file: queue[i] });
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
        isRequired
      />

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground">
          Documents <span className="text-destructive">*</span>
        </label>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
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
          accept={ACCEPTED_TYPES.join(',')}
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
        disabled={files.length === 0 || !selectedAgentId}
        onClick={handleUpload}
        icon={<Upload className="size-4" />}
      >
        {files.length > 1 ? `Upload ${files.length} files` : 'Upload document'}
      </CustomButton>
    </div>
  );
};

export default DocumentUpload;
