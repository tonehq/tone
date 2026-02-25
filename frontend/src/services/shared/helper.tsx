import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  CallReceived as InboundIcon,
  CallMade as OutboundIcon,
} from '@mui/icons-material';
import { Box, Chip, IconButton, Tooltip, Typography } from '@mui/material';
import { GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import React from 'react';

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
  onDelete?: (row: RowData) => void;
}

const ActionMenu: React.FC<ActionMenuProps> = ({ row, onEdit, onDelete }) => {
  const stopPropagation = (e: React.MouseEvent) => e.stopPropagation();

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Tooltip title="Edit">
        <IconButton
          size="small"
          onClick={(e) => {
            stopPropagation(e);
            onEdit?.(row);
          }}
          sx={{ color: 'text.secondary' }}
        >
          <EditIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Tooltip title="Delete">
        <IconButton
          size="small"
          onClick={(e) => {
            stopPropagation(e);
            onDelete?.(row);
          }}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

/* ===================== COLUMN BUILDER ===================== */

export const constructTable = (
  columns: ColumnConfig[],
  onEdit?: (row: RowData) => void,
  onDelete?: (row: RowData) => void,
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
            ? new Date(params.value).toLocaleString(undefined, {
                year: 'numeric',
                month: 'short',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })
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
                  <InboundIcon sx={{ fontSize: 16, color: '#10b981' }} />
                ) : (
                  <OutboundIcon sx={{ fontSize: 16, color: '#8b5cf6' }} />
                )
              }
              label={isInbound ? 'Inbound' : 'Outbound'}
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
