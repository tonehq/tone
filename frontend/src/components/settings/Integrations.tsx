'use client';

import { generateUUID } from '@/services/shared/helper';
import axiosInstance from '@/utils/axios';
import { Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
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
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useCallback, useEffect, useState } from 'react';

export interface IntegrationRow {
  id: string;
  name: string;
  auth_token: string;
  auth_sid: string;
  createdAt: string;
}

const dataGridSx = {
  borderRadius: '5px',
  overflow: 'hidden',
  '& .MuiDataGrid-columnHeaders': {
    backgroundColor: '#e5e7eb',
    borderTopLeftRadius: '5px',
    borderTopRightRadius: '5px',
  },
  '& .MuiDataGrid-columnHeadersInner': { backgroundColor: '#e5e7eb' },
  '& .MuiDataGrid-columnHeader': { backgroundColor: '#e5e7eb' },
  '& .MuiDataGrid-columnHeaderTitle': {
    fontWeight: 600,
    textTransform: 'uppercase',
    fontSize: '12px',
    color: '#475569',
  },
  '& .MuiDataGrid-columnSeparator': { display: 'none' },
  '& .MuiDataGrid-row': { borderBottom: '1px solid #e5e7eb' },
  '& .MuiDataGrid-cell': { display: 'flex', alignItems: 'center' },
};

const initialFormState = {
  name: '',
  auth_token: '',
  auth_sid: '',
};

function AddApiKeyModal({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; auth_token: string; auth_sid: string }) => void;
}) {
  const [name, setName] = useState(initialFormState.name);
  const [auth_token, setAuthToken] = useState(initialFormState.auth_token);
  const [auth_sid, setAuthSid] = useState(initialFormState.auth_sid);
  const theme = useTheme();

  const resetForm = useCallback(() => {
    setName(initialFormState.name);
    setAuthToken(initialFormState.auth_token);
    setAuthSid(initialFormState.auth_sid);
  }, []);

  const handleSubmit = () => {
    if (name.trim() && auth_token.trim() && auth_sid.trim()) {
      onSubmit({ name: name.trim(), auth_token: auth_token.trim(), auth_sid: auth_sid.trim() });
      resetForm();
      onClose();
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
          Add new API key
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
          />
        </Box>
        <Box sx={{ mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 0.5 }}>
            Auth SID
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter auth SID"
            value={auth_sid}
            onChange={(e) => setAuthSid(e.target.value)}
          />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, pt: 0 }}>
        <Button
          onClick={handleCancel}
          variant="outlined"
          sx={{ borderColor: theme.palette.divider }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!name.trim() || !auth_token.trim() || !auth_sid.trim()}
          sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function Integrations() {
  const [isLoading, setIsLoading] = useState(true);
  const [apiList, setApiList] = useState<IntegrationRow[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);

  const fetchApiList = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await axiosInstance.get<IntegrationRow[]>('/integrations');
      if (Array.isArray(response.data)) {
        setApiList(
          response.data.map((row: IntegrationRow & { created_at?: string }) => ({
            id: row.id,
            name: row.name,
            auth_token: row.auth_token ?? '••••••••',
            auth_sid: row.auth_sid ?? '',
            createdAt:
              row.createdAt ??
              (row as { created_at?: string }).created_at ??
              new Date().toISOString().slice(0, 10),
          })),
        );
      }
    } catch {
      setApiList([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApiList();
  }, [fetchApiList]);

  const handleSubmit = (data: { name: string; auth_token: string; auth_sid: string }) => {
    const newRow: IntegrationRow = {
      id: generateUUID(),
      name: data.name,
      auth_token: data.auth_token,
      auth_sid: data.auth_sid,
      createdAt: new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }),
    };
    setApiList((prev) => [...prev, newRow]);
    console.log(newRow, 'newRow');
    // TODO: call POST /integrations when backend is ready
    // await axiosInstance.post('/integrations', data);
  };

  const columns: GridColDef<IntegrationRow>[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
    },
    {
      field: 'auth_sid',
      headerName: 'Auth SID',
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
    },
    {
      field: 'auth_token',
      headerName: 'Auth Token',
      flex: 1,
      minWidth: 140,
      sortable: false,
      filterable: false,
    },
    {
      field: 'createdAt',
      headerName: 'Created at',
      flex: 1,
      minWidth: 140,
      sortable: false,
      filterable: false,
    },
  ];

  if (isLoading) {
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

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Integrations
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddModalOpen(true)}
          sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
        >
          Add new API key
        </Button>
      </Box>
      <DataGrid
        rows={apiList}
        columns={columns}
        disableRowSelectionOnClick
        autoHeight
        pageSizeOptions={[5, 10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={dataGridSx}
      />
      <AddApiKeyModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </Box>
  );
}
