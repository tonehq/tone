import React, { useEffect } from 'react';

import { Form, Input, Modal, Select } from 'antd';

import ButtonComponent from '../shared/ButtonComponent';

const { Option } = Select;

interface ModalComponentProps {
  open: boolean;
  onCancel: () => void;
  onInvite: (values: { name: string; email: string; role: string }) => void;
  loading?: boolean;
}

const ModalComponent: React.FC<ModalComponentProps> = ({ open, onCancel, onInvite, loading }) => {
  const [form] = Form.useForm();

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      onInvite(values);
    } catch (err) {
      // validation error
    }
  };

  useEffect(() => {
    if (open) {
      form.resetFields();
    }
  }, [open]);

  return (
    <Modal
      title="Invite User"
      open={open}
      onCancel={onCancel}
      footer={[
        <ButtonComponent key="cancel" text="Cancel" type="default" onClick={onCancel} />,
        <ButtonComponent
          key="invite"
          text="Invite"
          type="primary"
          active
          onClick={handleOk}
          loading={loading}
        />,
      ]}
      styles={{
        content: { borderRadius: 5 },
      }}
    >
      <Form requiredMark={false} form={form} layout="vertical">
        <Form.Item
          name="name"
          label="Full Name"
          rules={[{ required: true, message: 'Please enter name' }]}
        >
          <Input placeholder="John Doe" />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: 'Please enter email' },
            { type: 'email', message: 'Enter a valid email' },
          ]}
        >
          <Input placeholder="john@example.com" />
        </Form.Item>

        <Form.Item name="role" label="Role" initialValue="Member" rules={[{ required: true }]}>
          <Select>
            <Option value="Admin">Admin</Option>
            <Option value="Member">Member</Option>
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ModalComponent;
