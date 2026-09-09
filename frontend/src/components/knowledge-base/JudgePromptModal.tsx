'use client';

import { CustomModal } from '@/components/shared';

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
  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={`Judge prompt — ${configName}`}
      hideFooter
      width="sm:max-w-2xl"
    >
      {prompt ? (
        <pre className="whitespace-pre-wrap text-sm text-foreground">{prompt}</pre>
      ) : (
        <p className="text-sm text-muted-foreground">
          This config has no custom prompt — it scores with the built-in metrics only.
        </p>
      )}
    </CustomModal>
  );
}
