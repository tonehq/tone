'use client';

import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from 'react';

import {
  ACCEPTED_EXTENSIONS,
  ACCEPTED_TYPES,
  MAX_FILE_SIZE,
} from '@/components/knowledge-base/knowledgeBaseConstants';
import { showToast } from '@/utils/toast';

/**
 * Validate a picked file against the knowledge-base accepted extensions + size
 * ceiling, surfacing a toast on rejection. Shared so the "Add sources" and
 * "Replace file" flows reject files identically.
 */
export function validateKnowledgeBaseFile(f: File): boolean {
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
}

interface UseFileDropzoneOptions {
  /** Called with the validated files from a drop or file-input change. */
  onFiles: (files: File[]) => void;
}

/**
 * Drag-and-drop + hidden file-input plumbing shared by DocumentUpload and
 * EditDocument. Validates each file via `validateKnowledgeBaseFile` and only
 * forwards the valid ones — the caller owns dedupe / single-vs-multi semantics.
 */
export function useFileDropzone({ onFiles }: UseFileDropzoneOptions) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const acceptValidated = useCallback(
    (list: FileList | File[]) => {
      const validated = Array.from(list).filter(validateKnowledgeBaseFile);
      if (validated.length > 0) onFiles(validated);
    },
    [onFiles],
  );

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) acceptValidated(e.dataTransfer.files);
    },
    [acceptValidated],
  );

  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) acceptValidated(e.target.files);
      e.target.value = '';
    },
    [acceptValidated],
  );

  const openFilePicker = useCallback(() => fileInputRef.current?.click(), []);

  return {
    isDragging,
    fileInputRef,
    /** Value for the native `<input accept>` attribute. */
    acceptAttr: ACCEPTED_TYPES.join(','),
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleInputChange,
    openFilePicker,
  };
}
