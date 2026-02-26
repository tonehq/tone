'use client';

import { generateUUID } from '@/utils/helpers';
import { Add as AddIcon, Close as CloseIcon, MoreVert as MoreVertIcon } from '@mui/icons-material';
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
  Switch,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useState } from 'react';

export interface PublicKeyRow {
  id: string;
  name: string;
  keyValue: string;
  domains: string;
  abusePrevention: boolean;
  fraudProtection: boolean;
  createdAt: string;
}

const dataGridSx = {
  borderRadius: '5px',
  overflow: 'hidden',
  border: 'none',
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

function AddPublicKeyModal({
  open,
  onClose,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (data: {
    keyName: string;
    domains: string[];
    abusePrevention: boolean;
    fraudProtection: boolean;
  }) => void;
}) {
  const theme = useTheme();
  const [keyName, setKeyName] = useState('');
  const [domainInput, setDomainInput] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [abusePrevention, setAbusePrevention] = useState(false);
  const [fraudProtection, setFraudProtection] = useState(false);

  const handleAddDomain = () => {
    const d = domainInput.trim();
    if (d && !domains.includes(d)) {
      setDomains([...domains, d]);
      setDomainInput('');
    }
  };

  const handleSave = () => {
    if (keyName.trim()) {
      onSave({ keyName: keyName.trim(), domains, abusePrevention, fraudProtection });
      setKeyName('');
      setDomains([]);
      setAbusePrevention(false);
      setFraudProtection(false);
      onClose();
    }
  };

  const handleClose = () => {
    setKeyName('');
    setDomainInput('');
    setDomains([]);
    setAbusePrevention(false);
    setFraudProtection(false);
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
          Add Public Key
        </Typography>
        <IconButton size="small" onClick={handleClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
            Key Name
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="e.g. Staging-Frontend-PubKey (staging frontend public key)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
          />
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
            Allowed Domains
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              fullWidth
              size="small"
              placeholder="e.g. example.com"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddDomain())}
            />
            <Button variant="outlined" size="small" onClick={handleAddDomain}>
              + Add
            </Button>
          </Box>
          {domains.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
              {domains.map((d) => (
                <Chip
                  key={d}
                  label={d}
                  size="small"
                  onDelete={() => setDomains(domains.filter((x) => x !== d))}
                />
              ))}
            </Box>
          )}
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Abuse Prevention (Google reCAPTCHA)
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 1 }}>
            Utilize Google reCAPTCHA to prevent abuse on your applications (forms, widgets, etc.).
            The public key will require reCAPTCHA token to authenticate, so you must also add it on
            frontend. (
            <Typography
              component="a"
              href="#"
              variant="body2"
              color="primary"
              sx={{ textDecoration: 'underline' }}
            >
              See Docs
            </Typography>
            )
          </Typography>
          <Switch
            checked={abusePrevention}
            onChange={(e) => setAbusePrevention(e.target.checked)}
            color="primary"
          />
        </Box>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Fraud Protection
          </Typography>
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 1 }}>
            Once enabled, the system will automatically detect and limit suspicious requests based
            on IP address and destination number.
          </Typography>
          <Switch
            checked={fraudProtection}
            onChange={(e) => setFraudProtection(e.target.checked)}
            color="primary"
          />
        </Box>
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
          onClick={handleSave}
          disabled={!keyName.trim()}
          sx={{ bgcolor: '#000', '&:hover': { bgcolor: '#333' } }}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function PublicKeysTab() {
  const [publicKeys, setPublicKeys] = useState<PublicKeyRow[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<{ el: HTMLElement; row: PublicKeyRow } | null>(null);

  const handleSave = (data: {
    keyName: string;
    domains: string[];
    abusePrevention: boolean;
    fraudProtection: boolean;
  }) => {
    setPublicKeys((prev) => [
      ...prev,
      {
        id: generateUUID(),
        name: data.keyName,
        keyValue: '•••••••••••',
        domains: data.domains.join(', ') || '—',
        abusePrevention: data.abusePrevention,
        fraudProtection: data.fraudProtection,
        createdAt: new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }),
      },
    ]);
  };

  const handleMenuClose = () => setMenuAnchor(null);

  const columns: GridColDef<PublicKeyRow>[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 160 },
    { field: 'keyValue', headerName: 'Key Value', flex: 1, minWidth: 140 },
    { field: 'domains', headerName: 'Domains', flex: 1, minWidth: 120 },
    {
      field: 'abusePrevention',
      headerName: 'Abuse Prevention',
      flex: 1,
      minWidth: 140,
      renderCell: (params) => (params.value ? 'On' : 'Off'),
    },
    {
      field: 'fraudProtection',
      headerName: 'Fraud Protection',
      flex: 1,
      minWidth: 130,
      renderCell: (params) => (params.value ? 'On' : 'Off'),
    },
    { field: 'createdAt', headerName: 'Created at', flex: 1, minWidth: 120 },
    {
      field: 'actions',
      headerName: '',
      width: 56,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderCell: (params: GridRenderCellParams<PublicKeyRow>) => (
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
          Add Public Key
        </Button>
      </Box>
      <DataGrid
        rows={publicKeys}
        columns={columns}
        disableRowSelectionOnClick
        autoHeight
        pageSizeOptions={[5, 10, 25]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        sx={dataGridSx}
      />
      <AddPublicKeyModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSave={handleSave}
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
