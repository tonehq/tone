'use client';

import { CustomButton, CustomModal, SelectInput, TextInput } from '@/components/shared';
import type { CallLogFilterParam } from '@/types/callLog';
import { Plus, Trash2 } from 'lucide-react';
import React, { useCallback, useState } from 'react';

const FIELD_OPTIONS = [
  { value: 'status', label: 'Status' },
  { value: 'transport_type', label: 'Transport Type' },
  { value: 'from_number', label: 'From Number' },
  { value: 'to_number', label: 'To Number' },
  { value: 'duration_seconds', label: 'Duration (seconds)' },
  { value: 'started_at', label: 'Started At' },
  { value: 'ended_at', label: 'Ended At' },
];

const FILTER_FIELD_OPTIONS = [{ value: 'none', label: 'Select field' }, ...FIELD_OPTIONS];

const OPERATOR_OPTIONS = [
  { value: 'equal_to', label: 'Equal To' },
  { value: 'greater_than', label: 'Greater Than' },
  { value: 'less_than', label: 'Less Than' },
  { value: 'between', label: 'Between' },
  { value: 'in', label: 'In' },
  { value: 'contains', label: 'Contains' },
];

const SORT_FIELD_OPTIONS = [{ value: 'none', label: 'None' }, ...FIELD_OPTIONS];

const SORT_ORDER_OPTIONS = [
  { value: 'asc', label: 'Ascending' },
  { value: 'desc', label: 'Descending' },
];

interface FilterRow {
  field: string;
  operator: string;
  value: string;
  value2: string;
}

interface FilterSortModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (filters: CallLogFilterParam[], sortBy?: string, sortOrder?: 'asc' | 'desc') => void;
  currentFilters: CallLogFilterParam[];
  currentSortBy?: string;
  currentSortOrder?: 'asc' | 'desc';
}

const FilterSortModal: React.FC<FilterSortModalProps> = ({
  open,
  onClose,
  onApply,
  currentFilters,
  currentSortBy,
  currentSortOrder,
}) => {
  const [filterRows, setFilterRows] = useState<FilterRow[]>(() =>
    currentFilters.length > 0
      ? currentFilters.map((f) => ({
          field: f.field,
          operator: f.operator,
          value: Array.isArray(f.value) ? String(f.value[0] ?? '') : String(f.value),
          value2: Array.isArray(f.value) ? String(f.value[1] ?? '') : '',
        }))
      : [{ field: 'none', operator: 'equal_to', value: '', value2: '' }],
  );
  const [sortBy, setSortBy] = useState(currentSortBy ?? 'none');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(currentSortOrder ?? 'desc');

  const addRow = useCallback(() => {
    setFilterRows((prev) => [
      ...prev,
      { field: 'none', operator: 'equal_to', value: '', value2: '' },
    ]);
  }, []);

  const removeRow = useCallback((index: number) => {
    setFilterRows((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateRow = useCallback((index: number, updates: Partial<FilterRow>) => {
    setFilterRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...updates } : row)));
  }, []);

  const handleApply = useCallback(() => {
    const validFilters: CallLogFilterParam[] = filterRows
      .filter((row) => row.field && row.field !== 'none' && row.operator && row.value)
      .map((row) => {
        let value: string | number | (string | number)[] = row.value;
        if (row.operator === 'between') {
          value = [row.value, row.value2];
        } else if (row.operator === 'in') {
          value = row.value.split(',').map((v) => v.trim());
        }
        return { field: row.field, operator: row.operator, value };
      });

    const appliedSortBy = sortBy === 'none' ? undefined : sortBy;
    onApply(validFilters, appliedSortBy, sortOrder);
  }, [filterRows, sortBy, sortOrder, onApply]);

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Filters & Sort"
      width="sm:max-w-2xl"
      footer={null}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-foreground">Filters</h3>
          {filterRows.map((row, index) => (
            <div key={index} className="flex items-end gap-2">
              <SelectInput
                name={`filter-field-${index}`}
                label={index === 0 ? 'Field' : undefined}
                options={FILTER_FIELD_OPTIONS}
                value={row.field}
                onValueChange={(v) => updateRow(index, { field: v })}
                placeholder="Select field"
                triggerClassName="w-[150px]"
              />
              <SelectInput
                name={`filter-operator-${index}`}
                label={index === 0 ? 'Operator' : undefined}
                options={OPERATOR_OPTIONS}
                value={row.operator}
                onValueChange={(v) => updateRow(index, { operator: v })}
                placeholder="Operator"
                triggerClassName="w-[140px]"
              />
              <TextInput
                name={`filter-value-${index}`}
                label={index === 0 ? 'Value' : undefined}
                placeholder="Value"
                value={row.value}
                onChange={(e) => updateRow(index, { value: e.target.value })}
              />
              {row.operator === 'between' && (
                <TextInput
                  name={`filter-value2-${index}`}
                  label={index === 0 ? 'Value 2' : undefined}
                  placeholder="Value 2"
                  value={row.value2}
                  onChange={(e) => updateRow(index, { value2: e.target.value })}
                />
              )}
              <CustomButton
                type="text"
                size="icon-sm"
                onClick={() => removeRow(index)}
                disabled={filterRows.length <= 1}
              >
                <Trash2 className="size-4 text-muted-foreground" />
              </CustomButton>
            </div>
          ))}
          <CustomButton type="text" size="sm" icon={<Plus className="size-4" />} onClick={addRow}>
            Add Filter
          </CustomButton>
        </div>

        <hr className="border-border" />

        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-foreground">Sort</h3>
          <div className="flex items-end gap-2">
            <SelectInput
              name="sort-field"
              label="Sort By"
              options={SORT_FIELD_OPTIONS}
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
        </div>

        <div className="flex justify-end gap-2 pt-2">
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

export default FilterSortModal;
