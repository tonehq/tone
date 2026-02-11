'use client';

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
    Switch,
    Tab,
    Tabs,
    TextField,
    Typography,
    useTheme,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useState } from 'react';

/* ----- Types ----- */
interface ApiKeyRow {
  id: string;
  name: string;
  keyValue: string;
  masked: boolean;
  createdAt: string;
  tag?: string;
}

interface PublicKeyRow {
  id: string;
  name: string;
  keyValue: string;
  domains: string;
  abusePrevention: boolean;
  fraudProtection: boolean;
  createdAt: string;
}

/* ----- Mock data (replace with API) ----- */
const defaultApiKeys: ApiKeyRow[] = [
  {
    id: '1',
    name: 'Make retell testing',
    keyValue: '•••••••••••',
    masked: true,
    createdAt: '01/20/2026, 22:36',
  },
  {
    id: '2',
    name: 'Secret Key',
    keyValue: 'key_f128d39f3e6e015a3e18b3963a0b',
    masked: false,
    createdAt: '01/20/2026, 11:26',
    tag: 'Webhook',
  },
];

const defaultPublicKeys: PublicKeyRow[] = [];

/* ----- Tab panel helper ----- */
function TabPanel({
  children,
  value,
  index,
}: {
  children: React.ReactNode;
  value: number;
  index: number;
}) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

/* ----- Add API Key Modal ----- */
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
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
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

/* ----- Add Public Key Modal ----- */
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
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
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

/* ----- Main component ----- */
export default function Apikeys() {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>(defaultApiKeys);
  const [publicKeys, setPublicKeys] = useState<PublicKeyRow[]>(defaultPublicKeys);
  const [addApiKeyOpen, setAddApiKeyOpen] = useState(false);
  const [addPublicKeyOpen, setAddPublicKeyOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<{
    el: HTMLElement;
    row: ApiKeyRow | PublicKeyRow;
    type: 'api' | 'public';
  } | null>(null);

  const handleAddKey = () => {
    if (tabValue === 0) setAddApiKeyOpen(true);
    else setAddPublicKeyOpen(true);
  };

  const handleCreateApiKey = (name: string) => {
    setApiKeys((prev) => [
      ...prev,
      {
        id: String(prev.length + 1),
        name,
        keyValue: '•••••••••••',
        masked: true,
        createdAt: new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }),
      },
    ]);
  };

  const handleSavePublicKey = (data: {
    keyName: string;
    domains: string[];
    abusePrevention: boolean;
    fraudProtection: boolean;
  }) => {
    setPublicKeys((prev) => [
      ...prev,
      {
        id: String(prev.length + 1),
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

  const apiKeyColumns: GridColDef<ApiKeyRow>[] = [
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
            setMenuAnchor({ el: e.currentTarget, row: params.row, type: 'api' });
          }}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  const publicKeyColumns: GridColDef<PublicKeyRow>[] = [
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
            setMenuAnchor({ el: e.currentTarget, row: params.row, type: 'public' });
          }}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          API Keys
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddKey}
          sx={{ bgcolor: '#000', '&:hover': { bgcolor: '#333' } }}
        >
          Add Key
        </Button>
      </Box>

      <Tabs
        value={tabValue}
        onChange={(_, v: number) => setTabValue(v)}
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          '& .MuiTab-root': { textTransform: 'none', fontWeight: 600 },
          '& .Mui-selected': { color: 'primary.main' },
        }}
      >
        <Tab label="API Keys" />
        <Tab label="Public Keys" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        <DataGrid
          rows={apiKeys}
          columns={apiKeyColumns}
          disableRowSelectionOnClick
          autoHeight
          pageSizeOptions={[5, 10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          sx={{
            borderRadius: '5px',
            overflow: 'hidden',
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#e5e7eb',
              borderTopLeftRadius: '5px',
              borderTopRightRadius: '5px',
            },
            '& .MuiDataGrid-columnHeadersInner': {
              backgroundColor: '#e5e7eb',
            },
            '& .MuiDataGrid-columnHeader': {
              backgroundColor: '#e5e7eb',
            },

            '& .MuiDataGrid-columnHeaderTitle': {
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: '12px',
              color: '#475569',
            },

            '& .MuiDataGrid-columnSeparator': {
              display: 'none',
            },

            '& .MuiDataGrid-row': {
              borderBottom: '1px solid #e5e7eb',
            },

            '& .MuiDataGrid-cell': {
              display: 'flex',
              alignItems: 'center',
            },
          }}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <DataGrid
          rows={publicKeys}
          columns={publicKeyColumns}
          disableRowSelectionOnClick
          autoHeight
          pageSizeOptions={[5, 10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          sx={{
            borderRadius: '5px',
            overflow: 'hidden',
            border: 'none',
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#e5e7eb',
              borderTopLeftRadius: '5px',
              borderTopRightRadius: '5px',
            },
            '& .MuiDataGrid-columnHeadersInner': {
              backgroundColor: '#e5e7eb',
            },
            '& .MuiDataGrid-columnHeader': {
              backgroundColor: '#e5e7eb',
            },

            '& .MuiDataGrid-columnHeaderTitle': {
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: '12px',
              color: '#475569',
            },

            '& .MuiDataGrid-columnSeparator': {
              display: 'none',
            },

            '& .MuiDataGrid-row': {
              borderBottom: '1px solid #e5e7eb',
            },

            '& .MuiDataGrid-cell': {
              display: 'flex',
              alignItems: 'center',
            },
          }}
        />
      </TabPanel>

      <AddApiKeyModal
        open={addApiKeyOpen}
        onClose={() => setAddApiKeyOpen(false)}
        onCreate={handleCreateApiKey}
      />
      <AddPublicKeyModal
        open={addPublicKeyOpen}
        onClose={() => setAddPublicKeyOpen(false)}
        onSave={handleSavePublicKey}
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
