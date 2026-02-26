'use client';

import { generateUUID } from '@/services/shared/helper';
import {
  Add as AddIcon,
  Close as CloseIcon,
  Key as KeyIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useState } from 'react';

export interface ApiKeyRow {
  id: string;
  name: string;
  keyValue: string;
  masked: boolean;
  createdAt: string;
  tag?: string;
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

function AddApiKeyModal({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
}) {
  const [name, setName] = useState('');
  const theme = useTheme();

  const handleCreate = () => {
    if (name.trim()) {
      onCreate(name.trim());
      setName('');
      onClose();
    }
  };

  const handleClose = () => {
    setName('');
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { borderRadius: '5px' } }}
    >
      <DialogTitle
        sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}
      >
        <Typography component="span" variant="h6" sx={{ fontWeight: 600 }}>
          Add an API Key
        </Typography>
        <IconButton size="small" onClick={handleClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
          Name this key
        </Typography>
        <TextField
          fullWidth
          size="small"
          placeholder="e.g. Development"
          value={name}
          onChange={(e) => setName(e.target.value)}
          sx={{ mt: 0.5 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, pt: 0 }}>
        <Button
          onClick={handleClose}
          variant="outlined"
          sx={{ borderColor: theme.palette.divider }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleCreate}
          disabled={!name.trim()}
          sx={{ bgcolor: '#000', '&:hover': { bgcolor: '#333' } }}
        >
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function ApiKeysTab() {
  const theme = useTheme();
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<{ el: HTMLElement; row: ApiKeyRow } | null>(null);

  const handleCreate = (name: string) => {
    setApiKeys((prev) => [
      ...prev,
      {
        id: generateUUID(),
        name,
        keyValue: '•••••••••••',
        masked: true,
        createdAt: new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }),
      },
    ]);
  };

  const handleMenuClose = () => setMenuAnchor(null);

  const columns: GridColDef<ApiKeyRow>[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 200,
      renderCell: (params: GridRenderCellParams<ApiKeyRow>) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <KeyIcon sx={{ fontSize: 18, color: theme.palette.text.secondary }} />
          <Typography variant="body2">{params.row.name}</Typography>
          {params.row.tag && (
            <Chip
              label={params.row.tag}
              size="small"
              sx={{ height: 20, fontSize: '0.7rem' }}
              color="primary"
              variant="outlined"
            />
          )}
        </Box>
      ),
    },
    { field: 'keyValue', headerName: 'Key Value', flex: 1, minWidth: 180 },
    { field: 'createdAt', headerName: 'Created at', flex: 1, minWidth: 140 },
    {
      field: 'actions',
      headerName: '',
      width: 56,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderCell: (params: GridRenderCellParams<ApiKeyRow>) => (
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            setMenuAnchor({ el: e.currentTarget, row: params.row });
          }}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddModalOpen(true)}
          sx={{ bgcolor: '#000', '&:hover': { bgcolor: '#333' } }}
        >
          Add API Key
        </Button>
      </Box>
      <DataGrid
        rows={apiKeys}
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
        onCreate={handleCreate}
      />
      <Menu
        anchorEl={menuAnchor?.el}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>👁</ListItemIcon>
          <ListItemText>Reveal key</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ color: 'error.main' }}>
          <ListItemIcon sx={{ color: 'error.main' }}>🗑</ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
}
