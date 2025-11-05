import React from 'react';

import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  TableSortLabel,
} from '@mui/material';

import CustomPagination from '@/components/shared/CustomPagination';

import { TableColumn } from '@/utils/constructTableColumn';

import { DynamicScrollConfig, useDynamicScrollHeight } from '@/utils/table';

import styles from '@/styles/table.module.scss';

interface CustomTableProps<RecordType> {
  columns: TableColumn<RecordType>[];
  data: RecordType[];
  rowKey: string | ((record: RecordType) => string);
  loading?: boolean;
  showHeader?: boolean;
  size?: 'small' | 'medium' | 'large';
  style?: React.CSSProperties;
  withPagination?: boolean;
  pagination?: {
    current?: number;
    total?: number;
    pageSize?: number;
    onChange?: (page: number, pageSize?: number) => void;
    showSizeChanger?: boolean;
  };
  scroll?: { x?: number | true | string; y?: number | string };
  dynamicScrollConfig?: DynamicScrollConfig;
}

const CustomTable = <T extends object>(props: CustomTableProps<T>) => {
  const {
    columns,
    data,
    rowKey,
    loading,
    showHeader = true,
    size = 'medium',
    style,
    withPagination = false,
    pagination,
    scroll,
    dynamicScrollConfig,
  } = props;

  const calculatedScrollY = useDynamicScrollHeight(scroll?.y, dynamicScrollConfig);

  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record);
    }
    return (record as any)[rowKey]?.toString() || index.toString();
  };

  return (
    <div style={{ width: '100%' }} className={styles.customTableWrapper}>
      <TableContainer
        component={Paper}
        sx={{
          maxHeight: calculatedScrollY
            ? typeof calculatedScrollY === 'string'
              ? calculatedScrollY
              : `${calculatedScrollY}px`
            : 'none',
          border: '1px solid #e5e7eb',
          borderRadius: '6px',
          ...style,
        }}
      >
        <Table stickyHeader={!!calculatedScrollY} size={size === 'large' ? 'medium' : size}>
          {showHeader && (
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell
                    key={column.key}
                    sx={{
                      width: column.width,
                      minWidth: column.width,
                      fontWeight: 600,
                      backgroundColor: 'var(--color-background-secondary)',
                      borderBottom: '1px solid var(--color-border)',
                    }}
                  >
                    {column.sorter ? <TableSortLabel>{column.title}</TableSortLabel> : column.title}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
          )}
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={columns.length} align="center" sx={{ padding: 4 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} align="center" sx={{ padding: 4 }}>
                  No data
                </TableCell>
              </TableRow>
            ) : (
              data.map((record, index) => (
                <TableRow key={getRowKey(record, index)} hover>
                  {columns.map((column) => {
                    const value = (record as any)[column.dataIndex];
                    const renderedValue = column.render
                      ? column.render(value, record)
                      : (value ?? '-');
                    return (
                      <TableCell
                        key={column.key}
                        sx={{
                          width: column.width,
                          minWidth: 0,
                          borderBottom: '1px solid var(--color-border)',
                        }}
                      >
                        {renderedValue}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {withPagination && (
        <CustomPagination
          current={pagination?.current ?? 1}
          total={pagination?.total ?? data?.length}
          pageSize={pagination?.pageSize ?? 10}
          onChange={(page) =>
            pagination?.onChange && pagination.onChange(page, pagination?.pageSize ?? 10)
          }
          showSizeChanger={pagination?.showSizeChanger || false}
        />
      )}
    </div>
  );
};

export default CustomTable;
