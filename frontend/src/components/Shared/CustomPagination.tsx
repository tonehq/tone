import React from 'react';

import { Button, Pagination, Select, MenuItem, FormControl, Stack } from '@mui/material';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CustomPaginationProps {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
  showSizeChanger?: boolean;
}

const CustomPagination: React.FC<CustomPaginationProps> = ({
  current,
  total,
  pageSize,
  onChange,
  showSizeChanger,
}) => {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(pageSize, 1)));

  const goPrev = () => {
    if (current > 1) onChange(current - 1);
  };

  const goNext = () => {
    if (current < totalPages) onChange(current + 1);
  };

  return (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="space-between"
      sx={{ padding: '12px 8px' }}
    >
      <Button
        startIcon={<ChevronLeft size={16} />}
        onClick={goPrev}
        disabled={current === 1}
        variant="outlined"
        sx={{
          height: 36,
          borderRadius: 2,
          textTransform: 'none',
        }}
      >
        Previous
      </Button>

      <Pagination
        page={current}
        count={totalPages}
        onChange={(_, page) => onChange(page)}
        renderItem={(item) => {
          if (item.type === 'page') {
            const isActive = item.page === current;
            return (
              <Button
                variant={isActive ? 'contained' : 'outlined'}
                size="small"
                onClick={(e) => {
                  e.preventDefault();
                  if (item.page) onChange(item.page);
                }}
                sx={{
                  minWidth: 32,
                  width: 32,
                  height: 32,
                  padding: 0,
                  borderRadius: 1.5,
                  ...(isActive && {
                    backgroundColor: 'var(--color-primary)',
                    '&:hover': {
                      backgroundColor: 'var(--color-primary-dark)',
                    },
                  }),
                }}
              >
                {item.page}
              </Button>
            );
          }
          return null;
        }}
        hidePrevButton
        hideNextButton
      />

      <Button
        endIcon={<ChevronRight size={16} />}
        onClick={goNext}
        disabled={current === totalPages}
        variant="outlined"
        sx={{
          height: 36,
          borderRadius: 2,
          textTransform: 'none',
        }}
      >
        Next
      </Button>
    </Stack>
  );
};

export default CustomPagination;
