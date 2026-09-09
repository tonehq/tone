'use client';

import { Copy } from 'lucide-react';

import { CustomButton, CustomModal } from '@/components/shared';
import { copyToClipboard } from '@/utils/clipboard';
import { showToast } from '@/utils/toast';

interface JudgePromptModalProps {
  open: boolean;
  onClose: () => void;
  configName: string;
  prompt: string | null;
}

// Read-only viewer for a config's custom rubric prompt — opened from the
// compare columns (where the prompt is hidden to save space).
export default function JudgePromptModal({
  open,
  onClose,
  configName,
  prompt,
}: JudgePromptModalProps) {
  const handleCopy = async () => {
    if (!prompt) return;
    if (await copyToClipboard(prompt)) {
      showToast.success('Copied', 'Judge prompt copied to clipboard.');
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Judge prompt"
      description={configName}
      hideFooter
      width="sm:max-w-2xl"
    >
      {prompt ? (
        <div className="flex flex-col gap-2">
          <div className="overflow-hidden rounded-lg border border-border bg-muted/40">
            <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
              <span className="text-xs font-medium text-muted-foreground">Rubric criteria</span>
              <CustomButton
                type="text"
                size="xs"
                icon={<Copy className="size-3.5" />}
                onClick={handleCopy}
              >
                Copy
              </CustomButton>
            </div>
            <pre className="max-h-[55vh] overflow-auto whitespace-pre-wrap px-4 py-3 font-mono text-sm leading-relaxed text-foreground">
              {prompt}
            </pre>
          </div>
          <p className="text-xs text-muted-foreground">
            Free-text criteria the judge grades against, run as the “correctness” metric.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
          This config has no custom prompt — it scores with the built-in metrics only.
        </div>
      )}
    </CustomModal>
  );
}
