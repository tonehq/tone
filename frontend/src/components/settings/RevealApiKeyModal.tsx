'use client';

import { Check, Copy, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import { showToast } from '@/utils/toast';

interface RevealApiKeyModalProps {
  open: boolean;
  onClose: () => void;
  apiKey: string | null;
  name: string | null;
}

/**
 * Shown exactly once, right after key creation. After this modal closes the key
 * is unrecoverable (only its SHA-256 hash is stored server-side).
 */
export default function RevealApiKeyModal({ open, onClose, apiKey, name }: RevealApiKeyModalProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) setCopied(false);
  }, [open]);

  const handleCopy = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      showToast.success('Copied to clipboard');
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast.error('Could not copy to clipboard');
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={name ? `API key created — ${name}` : 'API key created'}
      showCloseButton={false}
      // Custom single-action footer — the default two-button footer's Cancel is
      // meaningless here (there's nothing to cancel; the key already exists).
      footer={
        <CustomButton type="primary" onClick={onClose}>
          I've copied it — close
        </CustomButton>
      }
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <div className="text-sm">
            <p className="font-medium">You won't see this key again.</p>
            <p className="mt-0.5 text-xs opacity-80">
              Copy it now and store it somewhere safe. If you lose it, revoke this key and create a
              new one.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-2">
          <code className="flex-1 truncate font-mono text-sm text-foreground">{apiKey ?? ''}</code>
          <CustomButton
            type="default"
            size="sm"
            onClick={handleCopy}
            icon={copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          >
            {copied ? 'Copied' : 'Copy'}
          </CustomButton>
        </div>
      </div>
    </CustomModal>
  );
}
