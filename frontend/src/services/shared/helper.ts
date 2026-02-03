import { GridColDef } from '@mui/x-data-grid';

interface ColumnConfig {
  label: string;
  value: string;
  hidden?: boolean;
}

interface RowData {
  id: string | number;
  name?: string;
  avatar?: string;
  [key: string]: any;
}

export const constructTable = (columns: ColumnConfig[]): GridColDef<RowData>[] =>
  columns
    .filter((col) => !col.hidden)
    .map((col) => ({
      field: col.value,
      headerName: col.label,
      sortable: false,
      filterable: true,
      flex: 1,
    }));
