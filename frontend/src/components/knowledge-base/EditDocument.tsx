'use client';

import {
  CloudUpload,
  File as FileIcon,
  FileCode,
  FileSpreadsheet,
  FileText,
  Save,
  X,
} from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import TextInput from '@/components/shared/TextInput';
import { useRenameKnowledgeBase, useReplaceKnowledgeBaseFile } from '@/lib/api/knowledge-base';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
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
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface EditDocumentProps {
  document: KnowledgeBaseDocument;
  onSaved: (updated?: KnowledgeBaseDocument) => void;
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
      return <FileIcon className="size-5 text-muted-foreground" />;
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const EditDocument: React.FC<EditDocumentProps> = ({ document, onSaved }) => {
  const [fileName, setFileName] = useState(document.file_name);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const renameMutation = useRenameKnowledgeBase();
  const replaceMutation = useReplaceKnowledgeBaseFile();

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

  const setFromList = useCallback(
    (list: FileList | File[]) => {
      const arr = Array.from(list);
      if (arr.length === 0) return;
      const candidate = arr[0];
      if (!validateFile(candidate)) return;
      setReplacementFile(candidate);
      // If the user never edited the name field, follow the new file's name.
      if (fileName.trim() === document.file_name.trim()) {
        setFileName(candidate.name);
      }
    },
    [validateFile, fileName, document.file_name],
  );

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
      if (e.dataTransfer.files.length > 0) setFromList(e.dataTransfer.files);
    },
    [setFromList],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) setFromList(e.target.files);
      e.target.value = '';
    },
    [setFromList],
  );

  const trimmedName = fileName.trim();
  const nameChanged = trimmedName.length > 0 && trimmedName !== document.file_name.trim();
  const fileChanged = replacementFile != null;
  const canSave = trimmedName.length > 0 && (nameChanged || fileChanged);
  const saving = renameMutation.isPending || replaceMutation.isPending;

  const handleSave = async () => {
    if (!canSave) return;
    if (!trimmedName) {
      showToast.error('Name required', 'Please enter a file name before saving.');
      return;
    }
    try {
      if (fileChanged && replacementFile) {
        // Single backend call handles file swap + optional rename.
        const updated = await replaceMutation.mutateAsync({
          id: document.id,
          file: replacementFile,
          fileName: nameChanged ? trimmedName : undefined,
        });
        showToast.success(
          nameChanged ? 'File replaced & renamed' : 'File replaced',
          'Changes saved successfully.',
        );
        onSaved(updated);
        return;
      }
      if (nameChanged) {
        const updated = await renameMutation.mutateAsync({
          id: document.id,
          fileName: trimmedName,
        });
        showToast.success('Document renamed');
        onSaved(updated);
        return;
      }
      onSaved();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-5 overflow-hidden">
      <TextInput
        name="file_name"
        label="File name"
        value={fileName}
        onChange={(e) => setFileName(e.target.value)}
        placeholder="document.pdf"
        isRequired
        autoFocus
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !replacementFile) {
            e.preventDefault();
            handleSave();
          }
        }}
      />

      <div>
        <div className="mb-1.5 flex items-baseline justify-between">
          <label className="block text-sm font-medium text-foreground">
            Replace file{' '}
            <span className="text-xs font-normal text-muted-foreground">(optional)</span>
          </label>
          {replacementFile && (
            <button
              type="button"
              onClick={() => setReplacementFile(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear
            </button>
          )}
        </div>

        {!replacementFile ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              'relative flex min-h-[110px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed transition-all',
              isDragging
                ? 'scale-[1.01] border-primary bg-primary/10'
                : 'border-border hover:border-primary/50 hover:bg-accent/40',
            )}
          >
            <div className="flex flex-col items-center gap-2 px-6 py-5">
              <div
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-xl transition-colors',
                  isDragging ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary',
                )}
              >
                <CloudUpload className="size-5" />
              </div>
              <div className="text-center">
                <p className="text-sm text-foreground">
                  Drop or{' '}
                  <span className="font-medium text-primary underline-offset-2 hover:underline">
                    browse
                  </span>{' '}
                  to replace
                </p>
                <p className="mt-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                  PDF · DOCX · TXT · CSV · JSON · max 10 MB
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/40 px-3.5 py-2.5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-background ring-1 ring-border">
              {getFileIcon(replacementFile.name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">{replacementFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(replacementFile.size)} · replaces current file
              </p>
            </div>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={() => setReplacementFile(null)}
              className="shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Remove replacement file"
              icon={<X className="size-4" />}
            />
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      <CustomButton
        type="primary"
        fullWidth
        loading={saving}
        disabled={!canSave}
        onClick={handleSave}
        icon={<Save className="size-4" />}
      >
        Save changes
      </CustomButton>
    </div>
  );
};

export default EditDocument;
