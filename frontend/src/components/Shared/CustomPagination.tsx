import type { SelectProps } from 'antd';
import { Button, Pagination } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import React from 'react';

type CustomPaginationProps = {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
  showSizeChanger?: boolean | SelectProps<any, DefaultOptionType>;
};

const CustomPagination: React.FC<CustomPaginationProps> = ({ current, total, pageSize, onChange, showSizeChanger }) => {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(pageSize, 1)));

  const goPrev = () => {
    if (current > 1) onChange(current - 1);
  };
  const goNext = () => {
    if (current < totalPages) onChange(current + 1);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 8px' }}>
      <Button
        icon={<ChevronLeft size={16} />}
        onClick={goPrev}
        disabled={current === 1}
        style={{
          height: 36,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        Previous
      </Button>

      <Pagination
        current={current}
        total={total}
        pageSize={pageSize}
        showSizeChanger={showSizeChanger}
        onChange={(page) => onChange(page)}
        itemRender={(page, type, original) => {
          if (type === 'page') {
            const isActive = page === current;
            return (
              <Button
                type={isActive ? 'primary' : 'default'}
                size="small"
                style={{
                  width: 32,
                  height: 32,
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 6,
                }}
              >
                {page}
              </Button>
            );
          }
          // hide prev/next items since we render custom buttons
          return <span style={{ display: 'none' }} />;
        }}
        showLessItems
        responsive
      />

      <Button
        icon={<ChevronRight size={16} />}
        iconPosition="end"
        onClick={goNext}
        disabled={current === totalPages}
        style={{
          height: 36,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        Next
      </Button>
    </div>
  );
};

export default CustomPagination;


