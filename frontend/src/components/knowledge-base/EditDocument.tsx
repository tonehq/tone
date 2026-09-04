'use client';

import { CloudUpload, Save, X } from 'lucide-react';
import React, { useCallback, useState } from 'react';

import { formatFileSize, getFileIcon } from '@/components/knowledge-base/knowledgeBaseHelpers';
import CustomButton from '@/components/shared/CustomButton';
import CustomModal from '@/components/shared/CustomModal';
import TextInput from '@/components/shared/TextInput';
import { useFileDropzone } from '@/hooks/useFileDropzone';
import { useRenameKnowledgeBase, useReplaceKnowledgeBaseFile } from '@/lib/api/knowledge-base';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface EditDocumentProps {
  document: KnowledgeBaseDocument;
  onSaved: (updated?: KnowledgeBaseDocument) => void;
}

const EditDocument: React.FC<EditDocumentProps> = ({ document, onSaved }) => {
  const [fileName, setFileName] = useState(document.file_name);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);

  const renameMutation = useRenameKnowledgeBase();
  const replaceMutation = useReplaceKnowledgeBaseFile();

  // Validation happens in the hook; this only takes the first validated file
  // and (when the name field is still untouched) follows the new file's name.
  const acceptReplacement = useCallback(
    (list: File[]) => {
      const candidate = list[0];
      if (!candidate) return;
      setReplacementFile(candidate);
      if (fileName.trim() === document.file_name.trim()) {
        setFileName(candidate.name);
      }
    },
    [fileName, document.file_name],
  );

  const {
    isDragging,
    fileInputRef,
    acceptAttr,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleInputChange,
    openFilePicker,
  } = useFileDropzone({ onFiles: acceptReplacement });

  const trimmedName = fileName.trim();
  const nameChanged = trimmedName.length > 0 && trimmedName !== document.file_name.trim();
  const fileChanged = replacementFile != null;
  const canSave = trimmedName.length > 0 && (nameChanged || fileChanged);
  const saving = renameMutation.isPending || replaceMutation.isPending;

  // The actual mutation. Callers must have already validated + (for a file
  // replace) confirmed the destructive re-ingest via ``handleSaveClick``.
  const performSave = async () => {
    if (!canSave || !trimmedName) return;
    try {
      if (fileChanged && replacementFile) {
        // Single backend call handles file swap + optional rename; the backend
        // also purges the old ingestion + evals + results and re-ingests.
        const updated = await replaceMutation.mutateAsync({
          id: document.id,
          file: replacementFile,
          fileName: nameChanged ? trimmedName : undefined,
        });
        setShowReplaceConfirm(false);
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

  // Save entry point. A file replacement is destructive (it deletes the doc's
  // existing ingestion, evals, and results), so it goes through a confirm
  // dialog first; a rename-only save is applied immediately.
  const handleSaveClick = () => {
    if (!canSave) return;
    if (!trimmedName) {
      showToast.error('Name required', 'Please enter a file name before saving.');
      return;
    }
    if (fileChanged) {
      setShowReplaceConfirm(true);
      return;
    }
    performSave();
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
            handleSaveClick();
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
            <CustomButton
              type="text"
              onClick={() => setReplacementFile(null)}
              className="!h-auto text-xs font-normal text-muted-foreground hover:text-foreground"
            >
              Clear
            </CustomButton>
          )}
        </div>

        {!replacementFile ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={openFilePicker}
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
                  PDF · DOCX · TXT · CSV · JSON · max 100 MB
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
          accept={acceptAttr}
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      <CustomButton
        type="primary"
        fullWidth
        loading={saving}
        disabled={!canSave}
        onClick={handleSaveClick}
        icon={<Save className="size-4" />}
      >
        Save changes
      </CustomButton>

      <CustomModal
        open={showReplaceConfirm}
        onClose={() => setShowReplaceConfirm(false)}
        title="Replace file?"
        description="Replacing the file permanently deletes this document's existing ingestion runs, chunks, and its evaluations and evaluation results. The new file is then re-ingested from scratch and evaluations are regenerated. This can't be undone."
        confirmText="Replace & re-ingest"
        cancelText="Cancel"
        confirmType="danger"
        confirmLoading={saving}
        onConfirm={performSave}
      />
    </div>
  );
};

export default EditDocument;
