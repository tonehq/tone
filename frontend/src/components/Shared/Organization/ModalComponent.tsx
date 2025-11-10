'use client';

import { useState } from 'react';

import {
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';

import { createOrganization } from '@/services/auth/helper';

import { showToast } from '@/utils/showToast';

import CustomButton from '../CustomButton';
import { Form, FormItem } from '../FormComponent';

const CreateOrganizationModal = (props: any) => {
  const { visible, setVisible, fetchOrganization } = props;
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [loading, setLoading] = useState(false);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value || '';
    const generatedSlug = value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    setName(value);
    setSlug(generatedSlug);
  };

  const handleOk = async () => {
    if (!name) {
      return;
    }
    setLoading(true);
    try {
      const res = await createOrganization({ name, slug });
      if (res.data) {
        showToast({
          status: 'success',
          message: 'Organization created successfully',
          variant: 'message',
        });
        await fetchOrganization();
      } else {
        showToast({
          status: 'error',
          message: 'Organization creation failed',
          variant: 'message',
        });
      }

      setName('');
      setSlug('');
      setVisible(false);
    } catch (err) {
      console.log('Validation Failed:', err);
      showToast({
        status: 'error',
        message: 'Organization creation failed',
        variant: 'message',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setName('');
    setSlug('');
    setVisible(false);
  };

  return (
    <Dialog
      open={visible}
      onClose={handleCancel}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '5px',
        },
      }}
    >
      <DialogTitle>
        <Box sx={{ fontSize: '18px', mb: 3, fontWeight: 500 }}>Create New Organization</Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Form layout="vertical">
            <FormItem
              name="name"
              label="Organization Name"
              rules={[{ required: true, message: 'Please enter organization name' }]}
            >
              <TextField
                placeholder="Enter organization name"
                value={name}
                onChange={handleNameChange}
                fullWidth
                variant="outlined"
                size="small"
              />
            </FormItem>

            <FormItem name="slug" label="Organization Slug">
              <TextField
                disabled
                placeholder="Organization slug"
                value={slug}
                fullWidth
                variant="outlined"
                size="small"
              />
            </FormItem>
          </Form>
        </Box>
      </DialogContent>
      <DialogActions sx={{ padding: 2, gap: 1 }}>
        <Stack direction="row" spacing={1} sx={{ width: '100%', justifyContent: 'flex-end' }}>
          <CustomButton
            text="Cancel"
            onClick={handleCancel}
            type="default"
            htmlType="button"
            sx={{ width: '100%' }}
          />
          <CustomButton
            text="Create"
            onClick={handleOk}
            type="primary"
            htmlType="submit"
            sx={{ width: '100%' }}
            loading={loading}
          />
        </Stack>
      </DialogActions>
    </Dialog>
  );
};

export default CreateOrganizationModal;
