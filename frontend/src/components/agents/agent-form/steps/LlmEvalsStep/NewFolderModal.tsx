import { useEffect, useState } from 'react';

import { CustomButton, CustomModal, TextInput } from '@/components/shared';

export default function NewFolderModal({
  open,
  onClose,
  onSubmit,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string) => Promise<void> | void;
  pending: boolean;
}) {
  const [name, setName] = useState('');

  useEffect(() => {
    if (!open) setName('');
  }, [open]);

  const submit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="New folder"
      description="Group scenarios by feature, flow, or persona — folders survive after their last scenario is deleted."
      width="max-w-md"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={pending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            loading={pending}
            disabled={pending || !name.trim()}
          >
            Create folder
          </CustomButton>
        </div>
      }
    >
      <TextInput
        name="folder_name"
        label="Folder name"
        placeholder="e.g. Refund flow"
        value={name}
        onChange={(e) => setName(e.target.value)}
        isRequired
        onKeyDown={handleKeyDown}
      />
    </CustomModal>
  );
}
