'use client';

import { CloudUpload, FileText, Upload, X } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import { useUploadKnowledgeBase } from '@/lib/api/knowledge-base';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'application/json',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const ACCEPTED_EXTENSIONS = ['pdf', 'txt', 'csv', 'json', 'docx'];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function fmt(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface KnowledgeBaseUploadModalProps {
  open: boolean;
  /** Null while creating a new agent. The upload is created standalone and
   * the agent form attaches it on save via the upload_ids payload. */
  agentId: string | null;
  onClose: () => void;
  /** Called once after a successful upload with the newly created upload IDs.
   * The agent form auto-selects those IDs and re-fetches the doc list. */
  onUploaded: (uploadedIds: string[]) => void;
}

export default function KnowledgeBaseUploadModal({
  open,
  agentId,
  onClose,
  onUploaded,
}: KnowledgeBaseUploadModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadKnowledgeBase();

  const validate = useCallback((f: File): boolean => {
    const ext = f.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      showToast.error(`Unsupported: ${f.name}`, `Allowed: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      return false;
    }
    if (f.size > MAX_FILE_SIZE) {
      showToast.error(`Too large: ${f.name}`, 'Max size is 10 MB');
      return false;
    }
    return true;
  }, []);

  const addFiles = useCallback(
    (next: FileList | File[]) => {
      const valid: File[] = [];
      for (const f of Array.from(next)) {
        const dup = files.some((ef) => ef.name === f.name && ef.size === f.size);
        if (!dup && validate(f)) valid.push(f);
      }
      if (valid.length > 0) setFiles((prev) => [...prev, ...valid]);
    },
    [files, validate],
  );

  const handleClose = () => {
    if (uploadMutation.isPending) return;
    setFiles([]);
    onClose();
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    // Fire uploads in parallel so the round-trips overlap. Successes are
    // reported once; failures stay in the list so the user can retry just
    // those without re-picking the survivors.
    const results = await Promise.allSettled(
      files.map((f) => uploadMutation.mutateAsync({ agentId, file: f })),
    );
    const uploadedIds: string[] = [];
    const failed: File[] = [];
    results.forEach((res, idx) => {
      if (res.status === 'fulfilled' && res.value?.id) {
        uploadedIds.push(String(res.value.id));
      } else {
        failed.push(files[idx]);
        if (res.status === 'rejected') handleApiError(res.reason);
      }
    });
    if (uploadedIds.length > 0) {
      showToast.success(
        uploadedIds.length === 1 ? 'Document uploaded' : `${uploadedIds.length} documents uploaded`,
        agentId
          ? 'They are attached to this agent and ready to use.'
          : 'Saved. They will be attached to the agent when you save.',
      );
      onUploaded(uploadedIds);
    }
    if (failed.length === 0) {
      setFiles([]);
      onClose();
    } else {
      setFiles(failed);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Upload to knowledge base"
      description={
        agentId
          ? 'Files are uploaded to this agent and auto-selected when they finish processing.'
          : 'Files are uploaded now and will be attached to the agent when you save.'
      }
      hideFooter
      width="sm:max-w-lg"
    >
      <div className="flex flex-col gap-4">
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setIsDragging(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
          }}
          className={cn(
            'flex min-h-[140px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed transition-all',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/40 hover:bg-muted/40',
          )}
        >
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <CloudUpload className="size-5" />
          </div>
          <p className="text-sm text-foreground">
            Drag &amp; drop or{' '}
            <span className="font-medium text-primary underline-offset-2 hover:underline">
              browse files
            </span>
          </p>
          <p className="text-[11px] text-muted-foreground">
            PDF · DOCX · TXT · CSV · JSON · max 10 MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPTED_TYPES.join(',')}
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = '';
            }}
          />
        </div>

        {files.length > 0 && (
          <div className="flex flex-col gap-2">
            {files.map((f, i) => (
              <div
                key={`${f.name}-${f.size}`}
                className="flex items-center gap-3 rounded-xl border border-border/70 bg-muted/30 px-3 py-2"
              >
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-background ring-1 ring-border">
                  <FileText className="size-4 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{f.name}</p>
                  <p className="text-xs text-muted-foreground">{fmt(f.size)}</p>
                </div>
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                  aria-label={`Remove ${f.name}`}
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  icon={<X className="size-4" />}
                />
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <CustomButton type="default" onClick={handleClose} disabled={uploadMutation.isPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            icon={<Upload className="size-4" />}
            onClick={handleUpload}
            loading={uploadMutation.isPending}
            disabled={files.length === 0}
          >
            {files.length > 1 ? `Upload ${files.length} files` : 'Upload'}
          </CustomButton>
        </div>
      </div>
    </CustomModal>
  );
}
