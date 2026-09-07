'use client';

import { useEffect, useState } from 'react';

import { EMPTY_DRAFT, type DraftQuestion } from '@/components/knowledge-base/evalsConstants';
import { CustomModal, TextAreaField, TextInput } from '@/components/shared';

interface AddEvalQuestionModalProps {
  open: boolean;
  saving: boolean;
  onClose: () => void;
  onSubmit: (draft: DraftQuestion) => Promise<void>;
}

// Manual "Add a question" form, moved off the main page into a modal so the
// review list stays front-and-center. Manages its own draft.
export default function AddEvalQuestionModal({
  open,
  saving,
  onClose,
  onSubmit,
}: AddEvalQuestionModalProps) {
  const [draft, setDraft] = useState<DraftQuestion>(EMPTY_DRAFT);

  useEffect(() => {
    if (open) setDraft(EMPTY_DRAFT);
  }, [open]);

  const update = <K extends keyof DraftQuestion>(key: K, value: DraftQuestion[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const canSubmit = draft.question.trim().length > 0 && draft.expected_answer.trim().length > 0;

  const handleConfirm = async () => {
    if (!canSubmit) return;
    await onSubmit(draft);
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Add a question"
      description="Add a Q&A pair to the selected version. It starts approved."
      confirmText="Add question"
      confirmLoading={saving}
      confirmDisabled={!canSubmit}
      onConfirm={handleConfirm}
    >
      <div className="flex flex-col gap-3">
        <TextAreaField
          name="draft-question"
          label="Question"
          placeholder="e.g. What time is checkout?"
          value={draft.question}
          onChange={(e) => update('question', e.target.value)}
          isRequired
          rows={2}
        />
        <TextAreaField
          name="draft-expected-answer"
          label="Expected answer"
          placeholder="e.g. Checkout is at 11:00 AM."
          value={draft.expected_answer}
          onChange={(e) => update('expected_answer', e.target.value)}
          isRequired
          rows={2}
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <TextInput
            name="draft-category"
            label="Category (optional)"
            placeholder="e.g. policy, pricing"
            value={draft.category}
            onChange={(e) => update('category', e.target.value)}
          />
          <TextInput
            name="draft-snippet"
            label="Expected source snippet (optional)"
            placeholder="Verbatim phrase from the KB doc"
            value={draft.expected_source_snippet}
            onChange={(e) => update('expected_source_snippet', e.target.value)}
          />
        </div>
      </div>
    </CustomModal>
  );
}
