import React, { useEffect, useState } from 'react';

import {
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  MenuItem,
  Select,
  TextField,
} from '@mui/material';

import CustomButton from '../shared/CustomButton';
import { Form, FormItem } from '../shared/FormComponent';

interface ModalComponentProps {
  open: boolean;
  onCancel: () => void;
  onInvite: (values: { name: string; email: string; role: string }) => void;
  loading?: boolean;
}

const ModalComponent: React.FC<ModalComponentProps> = ({ open, onCancel, onInvite, loading }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('Member');

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
      setRole('Member');
    }
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '5px',
        },
      }}
    >
      <DialogTitle>Invite User</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Form layout="vertical">
            <FormItem
              name="name"
              label="Full Name"
              rules={[{ required: true, message: 'Please enter name' }]}
            >
              <TextField
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                fullWidth
                variant="outlined"
                size="small"
              />
            </FormItem>

            <FormItem
              name="email"
              label="Email"
              rules={[{ required: true, message: 'Please enter email' }]}
            >
              <TextField
                placeholder="john@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                fullWidth
                variant="outlined"
                size="small"
                type="email"
              />
            </FormItem>

            <FormItem name="role" label="Role" rules={[{ required: true }]}>
              <FormControl fullWidth size="small">
                <Select value={role} onChange={(e) => setRole(e.target.value)}>
                  <MenuItem value="Admin">Admin</MenuItem>
                  <MenuItem value="Member">Member</MenuItem>
                </Select>
              </FormControl>
            </FormItem>
          </Form>
        </Box>
      </DialogContent>
      <DialogActions sx={{ padding: 2, gap: 1 }}>
        <CustomButton key="cancel" text="Cancel" type="default" onClick={onCancel} />
        <CustomButton
          key="invite"
          text="Invite"
          type="primary"
          onClick={handleOk}
          loading={loading}
        />
      </DialogActions>
    </Dialog>
  );
};

export default ModalComponent;
