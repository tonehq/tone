'use client';

import agentsAtom, { deleteAgentAtom, fetchAgentList } from '@/atoms/AgentsAtom';
import { constructTable } from '@/services/shared/helper';
import { Add as AddIcon, Search as SearchIcon } from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  InputAdornment,
  Paper,
  Snackbar,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import { DataGrid, GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import { useAtom } from 'jotai';
import { useRouter } from 'next/navigation';
import React, { useEffect, useRef, useState } from 'react';

const AgentListPage: React.FC = () => {
  const theme = useTheme();
  const router = useRouter();
  const [_paginationModel, _setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  });
  const [data] = useAtom(agentsAtom);
  const [, fetAgentsList] = useAtom(fetchAgentList);
  const [, removeAgent] = useAtom(deleteAgentAtom);
  const [loader, setLoader] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({ open: false, message: '', severity: 'success' });

  // Prevent double fetch with a ref flag
  const hasFetchedRef = useRef(false);

  const handleEdit = (row: { id?: number | string; agent_type?: string }) => {
    const type = (row.agent_type ?? 'inbound').toString().toLowerCase();
    const id = row.id ?? 0;
    if (!id) return;
    router.push(`/agents/edit/${type}/${id}`);
  };

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const init = async () => {
      setLoader(true);
      try {
        await fetAgentsList();
      } catch (err) {
        console.error(err);
      } finally {
        setLoader(false);
      }
    };

    init();
  }, []);

  const defaultColumns = [
    {
      key: 1,
      label: 'AGENT NAME',
      value: 'name',
    },
    {
      key: 2,
      label: 'PHONE NUMBER',
      value: 'phone_number',
    },
    {
      key: 3,
      label: 'LAST EDITED',
      value: 'updated_at',
    },
    {
      key: 4,
      label: 'AGENT TYPE',
      value: 'agent_type',
    },
    {
      key: 5,
      label: 'ACTION',
      value: 'action',
    },
  ];

  const handleDelete = async (row: { id?: number | string }) => {
    if (!row.id) return;
    try {
      await removeAgent(Number(row.id));
      setSnackbar({ open: true, message: 'Agent deleted successfully', severity: 'success' });
    } catch {
      setSnackbar({
        open: true,
        message: 'Failed to delete agent. Please try again.',
        severity: 'error',
      });
    }
  };

  const columns = constructTable(defaultColumns, handleEdit, handleDelete);

  return (
    <Box sx={{ p: 3, height: '100%' }}>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Agents
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            placeholder="Search..."
            size="small"
            sx={{ width: 200 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: theme.palette.text.secondary, fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => router.push('/agents/create/inbound')}
            sx={{
              backgroundColor: '#8b5cf6',
              '&:hover': {
                backgroundColor: '#7c3aed',
              },
            }}
          >
            Create Agent
          </Button>
        </Box>
      </Box>

      {/* Data Grid */}
      <Paper
        sx={{
          height: 'calc(100vh - 120px)',
          width: '100%',
          border: '1px solid #e2e8f0',
          borderRadius: '5px',
          overflow: 'hidden',
        }}
        elevation={0}
      >
        <DataGrid
          rows={data?.agentList}
          columns={columns as GridColDef<any>[]}
          loading={loader}
          paginationModel={_paginationModel}
          onPaginationModelChange={_setPaginationModel}
          pageSizeOptions={[10, 20, 50]}
          rowCount={data.agentList.length}
          paginationMode="server"
          disableRowSelectionOnClick
          onRowClick={(params) => console.log('Row clicked:', params)}
          sx={{
            border: 'none',
            borderRadius: '5px',
            overflow: 'hidden',
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#e5e7eb',
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
              color: '#475569',
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
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AgentListPage;
