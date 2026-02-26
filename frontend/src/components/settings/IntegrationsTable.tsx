'use client';

import type { IntegrationRow } from '@/atoms/IntegrationAtom';
import { Box, CircularProgress, IconButton } from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import { Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface IntegrationsTableProps {
  rows: IntegrationRow[];
  loading?: boolean;
  onEdit: (row: IntegrationRow) => void;
  onDelete: (id: number) => Promise<void>;
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
  '& .MuiDataGrid-columnSeparator': { color: '#475569' },
  '& .MuiDataGrid-menuIcon': { display: 'none' },
  '& .MuiDataGrid-row': { borderBottom: '1px solid #e5e7eb' },
  '& .MuiDataGrid-cell': { display: 'flex', alignItems: 'center' },
};

export default function IntegrationsTable({
  rows,
  loading,
  onEdit,
  onDelete,
}: IntegrationsTableProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  };

  const columns: GridColDef<IntegrationRow>[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
    },
    {
      field: 'account_sid',
      headerName: 'Account SID',
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
    },
    {
      field: 'auth_token',
      headerName: 'Auth Token',
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
    },
    {
      field: 'createdAt',
      headerName: 'Created at',
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      minWidth: 100,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderCell: (params) => {
        const isDeleting = deletingId === params.row.id;
        return (
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <IconButton
              size="small"
              onClick={() => onEdit(params.row)}
              disabled={isDeleting}
              aria-label="edit"
            >
              <Pencil size={18} color="#475569" />
            </IconButton>
            {isDeleting ? (
              <IconButton size="small" disabled>
                <CircularProgress size={18} color="error" />
              </IconButton>
            ) : (
              <IconButton
                size="small"
                onClick={() => handleDelete(params.row.id)}
                aria-label="delete"
              >
                <Trash2 size={18} color="red" />
              </IconButton>
            )}
          </Box>
        );
      },
    },
  ];

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          py: 8,
        }}
      >
        <CircularProgress size={36} />
      </Box>
    );
  }

  return (
    <DataGrid
      rows={rows}
      columns={columns}
      disableRowSelectionOnClick
      autoHeight
      pageSizeOptions={[5, 10, 25]}
      initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
      sx={dataGridSx}
    />
  );
}
