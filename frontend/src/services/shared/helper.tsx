import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  CallReceived as InboundIcon,
  MoreVert as MoreVertIcon,
  CallMade as OutboundIcon,
} from '@mui/icons-material';
import {
  Chip,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Typography,
} from '@mui/material';
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
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  const handleOpen = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation(); // prevent DataGrid row selection
    setAnchorEl(e.currentTarget);
  };

  const handleClose = () => setAnchorEl(null);

  return (
    <>
      <IconButton size="small" onClick={handleOpen}>
        <MoreVertIcon fontSize="small" />
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        MenuListProps={{ dense: true }}
      >
        <MenuItem
          onClick={() => {
            handleClose();
            onEdit?.(row);
          }}
        >
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => {
            handleClose();
            onDelete?.(row);
          }}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon sx={{ color: 'error.main' }}>
            <DeleteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </>
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
          const isInbound = true;

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
