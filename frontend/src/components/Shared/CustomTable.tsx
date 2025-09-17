import CustomPagination from '@/components/Shared/CustomPagination';
import styles from '@/styles/table.module.scss';
import { useAdaptiveTableScrollY } from '@/utils/table';
import { PaginationProps, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React from 'react';

type CustomTableProps<RecordType> = {
  columns: ColumnsType<RecordType>;
  data: RecordType[];
  rowKey: string | ((record: RecordType) => string);
  loading?: boolean;
  showHeader?: boolean;
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
  withPagination?: boolean;
  pagination?: PaginationProps;
  scroll?: { x?: number | true | string; y?: number | string };
  minScrollYPx?: number;
};

const CustomTable = <T extends object>(props: CustomTableProps<T>) => {
  const {
    columns,
    data,
    rowKey,
    loading,
    showHeader = true,
    size = 'large',
    style,
    withPagination = false,
    pagination,
    scroll,
    minScrollYPx = 50,
  } = props;

  const { scrollY, containerRef } = useAdaptiveTableScrollY({
    minScrollYPx,
  });

  const effectiveY = ((): number | undefined => {
    if (scroll && scroll.y !== undefined) return scroll.y as number;
    if (scrollY !== undefined) return scrollY;
    return minScrollYPx;
  })();

  return (
    <div style={{ width: '100%' }} className={styles.customTableWrapper} ref={containerRef}>
      <Table<T>
        columns={columns}
        dataSource={data}
        rowKey={rowKey as any}
        loading={loading}
        showHeader={showHeader}
        size={size}
        style={{ border: '1px solid #e5e7eb', borderRadius: 6, ...style }}
        pagination={false}
        sticky={!!effectiveY}
        scroll={{
          ...(scroll?.x !== undefined ? { x: scroll.x } : {}),
          ...(effectiveY !== undefined ? { y: effectiveY } : {}),
        }}
      />
      {withPagination && (
        <CustomPagination
          current={pagination?.current ?? 1}
          total={pagination?.total ?? data.length}
          pageSize={pagination?.pageSize ?? 10}
          onChange={(page) => pagination?.onChange && pagination?.onChange(page, pagination?.pageSize ?? 10)}
          showSizeChanger={pagination?.showSizeChanger || false}
        />
      )}
    </div>
  );
};

export default CustomTable;


