import React, { useEffect, useState } from 'react';

import { SelectInput, SelectOption, TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';
import Modal, { ModalAction } from '@/components/shared/Modal';

interface ModalComponentProps {
  open: boolean;
  onCancel: () => void;
  onInvite: (values: { name: string; email: string; role: string }) => void;
  loading?: boolean;
}

const ModalComponent: React.FC<ModalComponentProps> = ({ open, onCancel, onInvite, loading }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('member');

  const handleOk = async () => {
    if (!name || !email || !role) {
      return;
    }
    onInvite({ name, email, role });
  };

  useEffect(() => {
    if (open) {
      setName('');
      setEmail('');
      setRole('member');
    }
  }, [open]);

  const roleOptions: SelectOption[] = [
    { value: 'admin', label: 'Admin' },
    { value: 'member', label: 'Member' },
  ];

  const modalActions: ModalAction[] = [
    {
      key: 'cancel',
      text: 'Cancel',
      type: 'default',
      onClick: onCancel,
    },
    {
      key: 'invite',
      text: 'Invite',
      type: 'primary',
      onClick: handleOk,
      loading,
    },
  ];

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title="Invite User"
      actions={modalActions}
      titleClassName="!mb-0"
    >
      <Form layout="vertical" onFinish={handleOk}>
        <TextInput
          name="name"
          type="text"
          label="Full Name"
          placeholder="John Doe"
          value={name}
          onChange={(e) => setName(e.target.value)}
          isRequired
          rules={[{ required: true, message: 'Please enter name' }]}
        />
        <TextInput
          name="email"
          type="email"
          label="Email"
          placeholder="john@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          isRequired
          rules={[{ required: true, message: 'Please enter email' }]}
        />
        <SelectInput
          name="role"
          label="Role"
          value={role}
          onChange={(e) => setRole(e.target.value as string)}
          options={roleOptions}
          isRequired
          rules={[{ required: true }]}
        />
      </Form>
    </Modal>
  );
};

export default ModalComponent;
