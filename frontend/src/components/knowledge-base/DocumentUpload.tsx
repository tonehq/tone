'use client';

import { cn } from '@/utils/cn';
import { Upload, FileText, FileSpreadsheet, FileCode, File, X, CloudUpload } from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import SelectInput from '@/components/shared/SelectInput';

import { uploadDocuments } from '@/services/knowledgeBaseService';
import type { ApiAgent } from '@/types/agent';
import type { SelectOption } from '@/types/components';
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
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface DocumentUploadProps {
  agents: ApiAgent[];
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
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const agentOptions: SelectOption[] = agents.map((a) => ({
    label: a.name,
    value: String(a.id),
  }));

  const validateFile = useCallback((f: File): boolean => {
    const ext = f.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      showToast.error(`Unsupported: ${f.name}`, `Supported: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      return false;
    }
    if (f.size > MAX_FILE_SIZE) {
      showToast.error(`Too large: ${f.name}`, 'Maximum file size is 10 MB');
      return false;
    }
    return true;
  }, []);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const validated: File[] = [];
      for (const f of Array.from(newFiles)) {
        // Skip duplicates by name + size
        const isDuplicate = files.some((ef) => ef.name === f.name && ef.size === f.size);
        if (isDuplicate) continue;
        if (validateFile(f)) validated.push(f);
      }
      if (validated.length > 0) {
        setFiles((prev) => [...prev, ...validated]);
      }
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
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
      }
      e.target.value = '';
    },
    [addFiles],
  );

  const handleUpload = async () => {
    if (files.length === 0 || !selectedAgentId) return;

    setUploading(true);
    try {
      await uploadDocuments(selectedAgentId, files);
      const label = files.length === 1 ? 'Document uploaded' : `${files.length} documents uploaded`;
      showToast.success(label, 'Your documents have been uploaded successfully.');
      setFiles([]);
      setSelectedAgentId('');
      onUploadSuccess();
    } catch (error) {
      handleApiError(error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-5 overflow-hidden">
      {/* Agent selector */}
      <SelectInput
        name="agent"
        label="Agent"
        placeholder="Select an agent"
        options={agentOptions}
        value={selectedAgentId}
        onValueChange={setSelectedAgentId}
        loading={agentsLoading}
        isRequired
      />

      {/* Drop zone */}
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
            'relative flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/40 hover:bg-accent/50',
          )}
        >
          <div className="flex flex-col items-center gap-3 px-6 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <CloudUpload className="size-6 text-primary" />
            </div>
            <div className="text-center">
              <p className="text-sm text-foreground">
                Drag and drop files here or{' '}
                <span className="font-medium text-primary underline underline-offset-2">
                  click to browse
                </span>
              </p>
              <p className="mt-1.5 text-xs text-muted-foreground">
                Supported: PDF, TXT, CSV, JSON, DOCX
              </p>
              <p className="text-xs text-muted-foreground">Max file size: 10 MB</p>
            </div>
          </div>
        </div>

        {/* Selected files list */}
        {files.length > 0 && (
          <div className="mt-3 space-y-2">
            {files.map((file, index) => (
              <div
                key={`${file.name}-${file.size}`}
                className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2.5"
              >
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
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

      {/* Upload button */}
      <CustomButton
        type="primary"
        fullWidth
        loading={uploading}
        disabled={files.length === 0 || !selectedAgentId}
        onClick={handleUpload}
        icon={<Upload className="size-4" />}
      >
        {files.length > 1 ? `Upload ${files.length} Documents` : 'Upload Document'}
      </CustomButton>
    </div>
  );
};

export default DocumentUpload;
