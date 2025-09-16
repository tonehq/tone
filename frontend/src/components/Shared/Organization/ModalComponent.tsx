"use client";

import { Modal, Form, Input, Space, message } from "antd";
import ButtonComponent from "../UI Components/ButtonComponent";
import { useState } from "react";
import { createOrganization } from "@/services/auth/helper";

const CreateOrganizationModal = (props: any) => {
  const { visible, setVisible, fetchOrganization } = props;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value || "";
    const slug = value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-") 
      .replace(/^-+|-+$/g, ""); 
    form.setFieldsValue({ slug });
  };

  const handleOk = async () => {
    setLoading(true);
    try {
      const values = await form.validateFields();

      const res = await createOrganization(values);
      if(res.data) {
        message.success("Organization created successfully");
        await fetchOrganization();
      } else {
        message.error("Organization creation failed");
      }

      form.resetFields();
      setVisible(false);
    } catch (err) {
      console.log("Validation Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setVisible(false);
  };

  return (
    <>
      <Modal
        title={<div className="text-[18px] mb-6 font-[500]">Create New Organization</div>}
        open={visible}
        onOk={handleOk}
        onCancel={handleCancel}
        okText="Create"
        cancelText="Cancel"
        footer={false}
        styles={{
          content: { borderRadius: 5 },
        }}
      >
        <Form form={form} layout="vertical" requiredMark={false}>
          <Form.Item
            name="name"
            label="Organization Name"
            rules={[{ required: true, message: "Please enter organization name" }]}
          >
            <Input placeholder="Enter organization name" onChange={handleNameChange} />
          </Form.Item>

          <Form.Item
            name="slug"
            label="Organization Slug"
          >
            <Input disabled placeholder="Organization slug" />
          </Form.Item>

          <Form.Item>
            <Space className="w-full flex justify-end">
              <ButtonComponent
                text="Cancel"
                onClick={handleCancel}
                type="default"
                htmlType="button"
                className="w-full"
              />
              <ButtonComponent
                text="Create"
                onClick={handleOk}
                type="primary"
                htmlType="submit"
                active={true}
                className="w-full"
                loading={loading}
              />
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default CreateOrganizationModal;
