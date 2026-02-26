'use client';

import {
  deleteChannelAtom,
  type IntegrationRow,
  loadableChannelsAtom,
  upsertChannelAtom,
} from '@/atoms/IntegrationAtom';
import { Add as AddIcon } from '@mui/icons-material';
import { Alert, Box, Button, CircularProgress, Snackbar, Typography } from '@mui/material';
import { useAtom } from 'jotai';
import { useEffect, useState } from 'react';

import AddChannelModal from './AddChannelModal';
import IntegrationsTable from './IntegrationsTable';

interface SnackbarState {
  open: boolean;
  message: string;
  severity: 'success' | 'error';
}

export default function Integrations() {
  const [mounted, setMounted] = useState(false);
  const [channelsLoadable] = useAtom(loadableChannelsAtom);
  const [, upsertChannel] = useAtom(upsertChannelAtom);
  const [, removeChannel] = useAtom(deleteChannelAtom);
  const [modalOpen, setModalOpen] = useState(false);
  const [editRow, setEditRow] = useState<IntegrationRow | null>(null);
  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false,
    message: '',
    severity: 'success',
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const handleAdd = () => {
    setEditRow(null);
    setModalOpen(true);
  };

  const handleEdit = (row: IntegrationRow) => {
    setEditRow(row);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditRow(null);
  };

  const handleSubmit = async (data: {
    id?: number;
    name: string;
    auth_token: string;
    account_sid: string;
  }) => {
    const payload = {
      ...(data.id ? { id: data.id } : {}),
      name: data.name,
      type: 'TWILIO' as const,
      meta_data: {
        account_sid: data.account_sid,
        auth_token: data.auth_token,
      },
    };

    try {
      await upsertChannel(payload as any);
      showSnackbar(
        data.id ? 'Integration updated successfully' : 'Integration created successfully',
        'success',
      );
    } catch {
      showSnackbar('Failed to save integration. Please try again.', 'error');
      throw new Error('API call failed');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await removeChannel(id);
      showSnackbar('Integration deleted successfully', 'success');
    } catch {
      showSnackbar('Failed to delete integration. Please try again.', 'error');
    }
  };

  if (!mounted) {
    return (
      <Box
        sx={{
          p: 2,
          width: '100%',
          height: '100%',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <CircularProgress variant="indeterminate" size={40} />
      </Box>
    );
  }

  const isTableLoading = channelsLoadable.state === 'loading';
  const rows = channelsLoadable.state === 'hasData' ? channelsLoadable.data : [];

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Integrations
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
        >
          Add new API key
        </Button>
      </Box>
      <IntegrationsTable
        rows={rows}
        loading={isTableLoading}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
      <AddChannelModal
        open={modalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmit}
        editData={editRow}
      />
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
