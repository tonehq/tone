import React from 'react';

import { PaginationProps, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import CustomPagination from '@/components/shared/CustomPagination';

import { DynamicScrollConfig, useDynamicScrollHeight } from '@/utils/table';

import styles from '@/styles/table.module.scss';

interface CustomTableProps<RecordType> {
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
  dynamicScrollConfig?: DynamicScrollConfig;
}

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
    dynamicScrollConfig,
  } = props;

  // Calculate dynamic scroll height based on scroll.y and window size
  const calculatedScrollY = useDynamicScrollHeight(scroll?.y, dynamicScrollConfig);

  // Merge scroll configuration with calculated height
  const finalScroll = {
    ...(scroll?.x !== undefined ? { x: scroll.x } : {}),
    ...(calculatedScrollY !== undefined ? { y: calculatedScrollY } : {}),
  };

  return (
    <div style={{ width: '100%' }} className={styles.customTableWrapper}>
      <Table<T>
        columns={columns}
        dataSource={data}
        rowKey={rowKey as any}
        loading={loading}
        showHeader={showHeader}
        size={size}
        style={{ border: '1px solid #e5e7eb', borderRadius: 6, ...style }}
        pagination={false}
        sticky={!!finalScroll?.y}
        scroll={Object.keys(finalScroll).length > 0 ? finalScroll : undefined}
      />
      {withPagination && (
        <CustomPagination
          current={pagination?.current ?? 1}
          total={pagination?.total ?? data?.length}
          pageSize={pagination?.pageSize ?? 10}
          onChange={(page) =>
            pagination?.onChange && pagination?.onChange(page, pagination?.pageSize ?? 10)
          }
          showSizeChanger={pagination?.showSizeChanger || false}
        />
      )}
    </div>
  );
};

export default CustomTable;
