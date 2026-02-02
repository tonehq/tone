'use client';

import agentsAtom, { fetchAgentList } from '@/atoms/AgentsAtom';
import { constructTable } from '@/services/shared/helper';
import { Agent } from '@/types/agent';
import {
  Add as AddIcon,
  CallReceived as InboundIcon,
  MoreVert as MoreVertIcon,
  CallMade as OutboundIcon,
  Search as SearchIcon
} from '@mui/icons-material';
import {
  Avatar,
  Box,
  Button,
  Chip,
  IconButton,
  InputAdornment,
  Paper,
  TextField,
  Typography,
  useTheme,
} from '@mui/material';
import {
  GridColDef,
  GridPaginationModel,
  GridRenderCellParams
} from '@mui/x-data-grid';
import { format } from 'date-fns';
import { useAtom } from 'jotai';
import React, { useEffect, useRef, useState } from 'react';
import CreateAgentModal from './CreateAgentModal';

const AgentListPage: React.FC = () => {
  const theme = useTheme();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  });
  const [data] = useAtom(agentsAtom);
  const [, fetAgentsList] = useAtom(fetchAgentList);
  const [loader, setLoader] = useState(false);

  // Prevent double fetch with a ref flag
  const hasFetchedRef = useRef(false);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  console.log(data, loader, 'loader');

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  const defaultColumns = [
    {
      key: 1,
      label: 'AGENT NAME', 
      value: 'name'
    }, 
    {
      key: 2,
      label: 'PHONE NUMBER',
      value: 'phone_number'
    },
    {
      key: 3,
      label: 'LAST EDITED',
      value: 'updated_at'
    },
    {
      key: 4,
      label: 'AGENT TYPE',
      value: 'agent_type'
    },
    {
      key: 5,
      label: 'ACTION',
      value: 'action'
    },
  ]
  const columns: GridColDef<Agent>[] = [
    {
      field: 'name',
      headerName: 'AGENT NAME',
      flex: 1,
      minWidth: 250,
      renderCell: (params: GridRenderCellParams<Agent>) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Avatar
            src={params.row.avatar}
            sx={{
              width: 36,
              height: 36,
              backgroundColor: params.row.avatar ? 'transparent' : '#e2e8f0',
              color: '#6b7280',
            }}
          >
            {!params.row.avatar && params.row.name.charAt(0).toUpperCase()}
          </Avatar>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {params.row.name}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'phoneNumber',
      headerName: 'PHONE NUMBER',
      width: 180,
      renderCell: (params: GridRenderCellParams<Agent>) => (
        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
          {params.row.phoneNumber || '—'}
        </Typography>
      ),
    },
    {
      field: 'lastEdited',
      headerName: 'LAST EDITED',
      width: 180,
      renderCell: (params: GridRenderCellParams<Agent>) => (
        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
          {formatDate(params.row.lastEdited)}
        </Typography>
      ),
    },
    {
      field: 'type',
      headerName: 'TYPE',
      width: 140,
      renderCell: (params: GridRenderCellParams<Agent>) => {
        const isInbound = params.row.type === 'inbound';
        return (
          <Chip
            icon={
              isInbound ? (
                <InboundIcon sx={{ fontSize: 16 }} />
              ) : (
                <OutboundIcon sx={{ fontSize: 16 }} />
              )
            }
            label={isInbound ? 'Inbound' : 'Outbound'}
            size="small"
            sx={{
              backgroundColor: isInbound
                ? 'rgba(16, 185, 129, 0.1)'
                : 'rgba(139, 92, 246, 0.1)',
              color: isInbound ? '#10b981' : '#8b5cf6',
              fontWeight: 500,
              '& .MuiChip-icon': {
                color: isInbound ? '#10b981' : '#8b5cf6',
              },
            }}
          />
        );
      },
    },
    {
      field: 'actions',
      headerName: '',
      width: 60,
      sortable: false,
      renderCell: () => (
        <IconButton size="small">
          <MoreVertIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  const column = constructTable(defaultColumns)

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
            onClick={() => setIsModalOpen(true)}
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
          height: 'calc(100vh - 180px)',
          width: '100%',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
        elevation={0}
      >
       
      </Paper>

      {/* Create Agent Modal */}
      <CreateAgentModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </Box>
  );
};

export default AgentListPage;
