import { Box, Chip, CircularProgress, IconButton, Tooltip, Typography } from '@mui/material';
import { GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import dayjs from 'dayjs';
import { Pencil, PhoneIncoming, PhoneOutgoing, Trash2 } from 'lucide-react';
import React, { useState } from 'react';

/* ===================== TYPES ===================== */

interface ColumnConfig {
  value: string;
  label: string;
  hidden?: boolean;
}

interface RowData {
  id?: string | number;
  [key: string]: any;
}

/* ===================== ACTION MENU ===================== */

interface ActionMenuProps {
  row: RowData;
  onEdit?: (row: RowData) => void;
  onDelete?: (row: RowData) => void | Promise<void>;
}

const ActionMenu: React.FC<ActionMenuProps> = ({ row, onEdit, onDelete }) => {
  const [deleting, setDeleting] = useState(false);
  const stopPropagation = (e: React.MouseEvent) => e.stopPropagation();

  const handleDelete = async (e: React.MouseEvent) => {
    stopPropagation(e);
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete(row);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Tooltip title="Edit">
        <IconButton
          size="small"
          disabled={deleting}
          onClick={(e) => {
            stopPropagation(e);
            onEdit?.(row);
          }}
          sx={{ color: 'text.secondary' }}
        >
          <Pencil size={18} color="#475569" />
        </IconButton>
      </Tooltip>
      {deleting ? (
        <IconButton size="small" disabled>
          <CircularProgress size={20} color="error" />
        </IconButton>
      ) : (
        <Tooltip title="Delete">
          <IconButton size="small" onClick={handleDelete} sx={{ color: 'error.main' }}>
            <Trash2 size={18} color="red" />
          </IconButton>
        </Tooltip>
      )}
    </Box>
  );
};

/* ===================== COLUMN BUILDER ===================== */

export const constructTable = (
  columns: ColumnConfig[],
  onEdit?: (row: RowData) => void,
  onDelete?: (row: RowData) => void | Promise<void>,
): GridColDef<RowData>[] =>
  columns
    .filter((col) => !col.hidden)
    .map<GridColDef<RowData>>((col) => ({
      field: col.value,
      headerName: col.label,
      flex: 1,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      align: 'center',
      headerAlign: 'center',

      renderCell: (
        params: GridRenderCellParams<RowData, string | number | null>,
      ): React.ReactNode => {
        /* ACTION COLUMN */
        if (col.value === 'action') {
          return <ActionMenu row={params.row} onEdit={onEdit} onDelete={onDelete} />;
        }

        /* DATE COLUMN */
        if (col.value === 'updated_at') {
          const value = params.value
            ? dayjs.unix(Number(params.value)).format('DD-MM-YYYY HH:mm:ss')
            : '-';

          return <Typography variant="body2">{value}</Typography>;
        }

        /* AGENT TYPE COLUMN */
        if (col.value === 'agent_type') {
          const raw = params.value;
          const isInbound =
            raw === 'inbound' || String(raw).toLowerCase() === 'inbound' || raw === 0;

          return (
            <Chip
              icon={
                isInbound ? (
                  <PhoneIncoming size={15} color="#10b981" />
                ) : (
                  <PhoneOutgoing size={15} color="#8b5cf6" />
                )
              }
              label={
                isInbound ? (
                  <Box sx={{ marginLeft: 1 }}>{'Inbound'}</Box>
                ) : (
                  <Box sx={{ marginLeft: 1 }}>{'Outbound'}</Box>
                )
              }
              size="small"
              sx={{
                backgroundColor: isInbound ? 'rgba(16, 185, 129, 0.1)' : 'rgba(139, 92, 246, 0.1)',
                color: isInbound ? '#10b981' : '#8b5cf6',
                fontWeight: 500,
              }}
            />
          );
        }

        /* DEFAULT CELL */
        return <Typography variant="body2">{params.value ?? '-'}</Typography>;
      },
    }));

export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
