'use client';

import type { IntegrationRow } from '@/atoms/IntegrationAtom';
import { Close as CloseIcon } from '@mui/icons-material';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';

interface AddChannelModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { id?: number; name: string; auth_token: string; account_sid: string }) => Promise<void>;
  editData?: IntegrationRow | null;
}

const initialFormState = {
  name: '',
  auth_token: '',
  account_sid: '',
};

export default function AddChannelModal({ open, onClose, onSubmit, editData }: AddChannelModalProps) {
  const [name, setName] = useState(initialFormState.name);
  const [auth_token, setAuthToken] = useState(initialFormState.auth_token);
  const [account_sid, setAccountSid] = useState(initialFormState.account_sid);
  const [saving, setSaving] = useState(false);
  const theme = useTheme();

  const isEdit = Boolean(editData);

  useEffect(() => {
    if (open && editData) {
      setName(editData.name);
      setAuthToken(editData.auth_token);
      setAccountSid(editData.account_sid);
    } else if (open) {
      setName(initialFormState.name);
      setAuthToken(initialFormState.auth_token);
      setAccountSid(initialFormState.account_sid);
    }
  }, [open, editData]);

  const resetForm = useCallback(() => {
    setName(initialFormState.name);
    setAuthToken(initialFormState.auth_token);
    setAccountSid(initialFormState.account_sid);
  }, []);

  const handleSubmit = async () => {
    if (!name.trim() || !auth_token.trim() || !account_sid.trim()) return;
    setSaving(true);
    try {
      await onSubmit({
        ...(editData ? { id: editData.id } : {}),
        name: name.trim(),
        auth_token: auth_token.trim(),
        account_sid: account_sid.trim(),
      });
      resetForm();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { borderRadius: '5px', width: '500px' } }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pb: 1,
        }}
      >
        <Typography component="span" variant="h6" sx={{ fontWeight: 600 }}>
          {isEdit ? 'Edit API key' : 'Add new API key'}
        </Typography>
        <IconButton size="small" onClick={handleCancel} aria-label="close">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1, mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 0.5 }}>
            Name
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="e.g. Twilio Production"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
          />
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 0.5 }}>
            Auth Token
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter auth token"
            type="password"
            value={auth_token}
            onChange={(e) => setAuthToken(e.target.value)}
            disabled={saving}
          />
        </Box>
        <Box sx={{ mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 0.5 }}>
            Account SID
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter account SID"
            value={account_sid}
            onChange={(e) => setAccountSid(e.target.value)}
            disabled={saving}
          />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, pt: 0 }}>
        <Button
          onClick={handleCancel}
          variant="outlined"
          disabled={saving}
          sx={{ borderColor: theme.palette.divider }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!name.trim() || !auth_token.trim() || !account_sid.trim() || saving}
          startIcon={saving ? <CircularProgress size={18} color="inherit" /> : undefined}
          sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
        >
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
