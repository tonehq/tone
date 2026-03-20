'use client';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import React, { useCallback, useState } from 'react';

const FIELD_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'status', label: 'Status' },
  { value: 'transport_type', label: 'Transport Type' },
  { value: 'from_number', label: 'From Number' },
  { value: 'to_number', label: 'To Number' },
  { value: 'duration_seconds', label: 'Duration (seconds)' },
  { value: 'started_at', label: 'Started At' },
  { value: 'ended_at', label: 'Ended At' },
];

const SORT_ORDER_OPTIONS = [
  { value: 'asc', label: 'Ascending' },
  { value: 'desc', label: 'Descending' },
];

interface SortModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (sortBy?: string, sortOrder?: 'asc' | 'desc') => void;
  currentSortBy?: string;
  currentSortOrder?: 'asc' | 'desc';
}

const SortModal: React.FC<SortModalProps> = ({
  open,
  onClose,
  onApply,
  currentSortBy,
  currentSortOrder,
}) => {
  const [sortBy, setSortBy] = useState(currentSortBy ?? 'none');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(currentSortOrder ?? 'desc');

  const handleApply = useCallback(() => {
    const appliedSortBy = sortBy === 'none' ? undefined : sortBy;
    onApply(appliedSortBy, sortOrder);
  }, [sortBy, sortOrder, onApply]);

  return (
    <CustomModal open={open} onClose={onClose} title="Sort" footer={null}>
      <div className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <SelectInput
            name="sort-field"
            label="Sort By"
            options={FIELD_OPTIONS}
            value={sortBy}
            onValueChange={(v) => setSortBy(v)}
            placeholder="Select field"
            triggerClassName="w-[200px]"
          />
          <SelectInput
            name="sort-order"
            label="Order"
            options={SORT_ORDER_OPTIONS}
            value={sortOrder}
            onValueChange={(v) => setSortOrder(v as 'asc' | 'desc')}
            triggerClassName="w-[150px]"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <CustomButton
            type="danger"
            onClick={() => {
              onApply(undefined, undefined);
            }}
            disabled={!currentSortBy}
          >
            Clear
          </CustomButton>
          <CustomButton type="default" onClick={onClose}>
            Cancel
          </CustomButton>
          <CustomButton type="primary" onClick={handleApply}>
            Apply
          </CustomButton>
        </div>
      </div>
    </CustomModal>
  );
};

export default SortModal;
