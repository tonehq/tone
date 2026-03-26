'use client';

import {
  CustomButton,
  CustomModal,
  MultiSelectField,
  SelectInput,
  TextInput,
} from '@/components/shared';
import { getFilterValues } from '@/services/callLogService';
import type { CallLogFilterParam } from '@/types/callLog';
import { handleApiError } from '@/utils/helpers';
import { Plus, Trash2 } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

const FIELD_OPTIONS = [
  { value: 'status', label: 'Status' },
  { value: 'transport_type', label: 'Transport Type' },
  { value: 'agent_name', label: 'Agent Name' },
  { value: 'agent_type', label: 'Agent Type' },
  { value: 'from_number', label: 'From Number' },
  { value: 'to_number', label: 'To Number' },
  { value: 'duration_seconds', label: 'Duration (seconds)' },
  { value: 'started_at', label: 'Started At' },
  { value: 'ended_at', label: 'Ended At' },
];

const FILTER_FIELD_OPTIONS = [{ value: 'none', label: 'Select field' }, ...FIELD_OPTIONS];

const CATEGORICAL_FIELDS = new Set(['status', 'transport_type', 'agent_name', 'agent_type']);
const DATETIME_FIELDS = new Set(['started_at', 'ended_at']);

const DATETIME_OPERATOR_OPTIONS = [
  { value: 'greater_than', label: 'After' },
  { value: 'less_than', label: 'Before' },
  { value: 'between', label: 'Between' },
];

const OPERATOR_OPTIONS = [
  { value: 'equal_to', label: 'Equal To' },
  { value: 'greater_than', label: 'Greater Than' },
  { value: 'less_than', label: 'Less Than' },
  { value: 'between', label: 'Between' },
  { value: 'in', label: 'In' },
  { value: 'contains', label: 'Contains' },
];

interface FilterRow {
  field: string;
  operator: string;
  value: string;
  value2: string;
  selectedValues: string[];
}

interface FilterModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (filters: CallLogFilterParam[]) => void;
  currentFilters: CallLogFilterParam[];
}

function toDatetimeLocal(unixTimestamp: number): string {
  const date = new Date(unixTimestamp * 1000);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function fromDatetimeLocal(datetimeStr: string): number {
  return Math.floor(new Date(datetimeStr).getTime() / 1000);
}

const FilterModal: React.FC<FilterModalProps> = ({ open, onClose, onApply, currentFilters }) => {
  const [filterRows, setFilterRows] = useState<FilterRow[]>(() =>
    currentFilters.length > 0
      ? currentFilters.map((f) => {
          const isCategorical = CATEGORICAL_FIELDS.has(f.field);
          const isDatetime = DATETIME_FIELDS.has(f.field);
          return {
            field: f.field,
            operator: isCategorical ? 'in' : f.operator,
            value: isCategorical
              ? ''
              : isDatetime && typeof f.value === 'number'
                ? toDatetimeLocal(f.value)
                : Array.isArray(f.value)
                  ? String(f.value[0] ?? '')
                  : String(f.value),
            value2:
              isDatetime && Array.isArray(f.value) && f.value[1]
                ? toDatetimeLocal(Number(f.value[1]))
                : Array.isArray(f.value) && !isCategorical
                  ? String(f.value[1] ?? '')
                  : '',
            selectedValues: isCategorical
              ? Array.isArray(f.value)
                ? f.value.map(String)
                : [String(f.value)]
              : [],
          };
        })
      : [{ field: 'none', operator: 'equal_to', value: '', value2: '', selectedValues: [] }],
  );

  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({});
  const [loadingOptions, setLoadingOptions] = useState<Record<string, boolean>>({});

  const fetchOptions = useCallback(
    async (fieldName: string) => {
      if (filterOptions[fieldName] || loadingOptions[fieldName]) return;
      setLoadingOptions((prev) => ({ ...prev, [fieldName]: true }));
      try {
        const data = await getFilterValues(fieldName);
        setFilterOptions((prev) => ({ ...prev, [fieldName]: data.values }));
      } catch (error) {
        handleApiError(error);
      } finally {
        setLoadingOptions((prev) => ({ ...prev, [fieldName]: false }));
      }
    },
    [filterOptions, loadingOptions],
  );

  useEffect(() => {
    filterRows.forEach((row) => {
      if (CATEGORICAL_FIELDS.has(row.field) && !filterOptions[row.field]) {
        fetchOptions(row.field);
      }
    });
  }, [filterRows, filterOptions, fetchOptions]);

  const addRow = useCallback(() => {
    setFilterRows((prev) => [
      ...prev,
      { field: 'none', operator: 'equal_to', value: '', value2: '', selectedValues: [] },
    ]);
  }, []);

  const removeRow = useCallback((index: number) => {
    setFilterRows((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateRow = useCallback((index: number, updates: Partial<FilterRow>) => {
    setFilterRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...updates } : row)));
  }, []);

  const handleFieldChange = useCallback(
    (index: number, newField: string) => {
      const isCategorical = CATEGORICAL_FIELDS.has(newField);
      const isDatetime = DATETIME_FIELDS.has(newField);
      updateRow(index, {
        field: newField,
        operator: isCategorical ? 'in' : isDatetime ? 'greater_than' : 'equal_to',
        value: '',
        value2: '',
        selectedValues: [],
      });
    },
    [updateRow],
  );

  const handleApply = useCallback(() => {
    const validFilters: CallLogFilterParam[] = filterRows
      .filter((row) => {
        if (!row.field || row.field === 'none') return false;
        if (CATEGORICAL_FIELDS.has(row.field)) return row.selectedValues.length > 0;
        return row.value !== '';
      })
      .map((row) => {
        if (CATEGORICAL_FIELDS.has(row.field)) {
          return { field: row.field, operator: 'in', value: row.selectedValues };
        }
        if (DATETIME_FIELDS.has(row.field)) {
          if (row.operator === 'between') {
            return {
              field: row.field,
              operator: row.operator,
              value: [fromDatetimeLocal(row.value), fromDatetimeLocal(row.value2)],
            };
          }
          return {
            field: row.field,
            operator: row.operator,
            value: fromDatetimeLocal(row.value),
          };
        }
        let value: string | number | (string | number)[] = row.value;
        if (row.operator === 'between') {
          value = [row.value, row.value2];
        } else if (row.operator === 'in') {
          value = row.value.split(',').map((v) => v.trim());
        }
        return { field: row.field, operator: row.operator, value };
      });

    onApply(validFilters);
  }, [filterRows, onApply]);

  const renderValueInput = (row: FilterRow, index: number) => {
    if (CATEGORICAL_FIELDS.has(row.field)) {
      const options = (filterOptions[row.field] ?? []).map((v) => ({ value: v, label: v }));
      return (
        <MultiSelectField
          name={`filter-value-${index}`}
          label={index === 0 ? 'Value' : undefined}
          options={options}
          value={row.selectedValues}
          onChange={(vals) => updateRow(index, { selectedValues: vals })}
          loading={loadingOptions[row.field] ?? false}
          className="min-w-[200px]"
        />
      );
    }

    if (DATETIME_FIELDS.has(row.field)) {
      return (
        <>
          <div className="flex flex-col">
            {index === 0 && (
              <label className="mb-1.5 text-sm font-medium" htmlFor={`filter-value-${index}`}>
                Value
              </label>
            )}
            <input
              id={`filter-value-${index}`}
              type="datetime-local"
              className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
              value={row.value}
              onChange={(e) => updateRow(index, { value: e.target.value })}
            />
          </div>
          {row.operator === 'between' && (
            <div className="flex flex-col">
              {index === 0 && (
                <label className="mb-1.5 text-sm font-medium" htmlFor={`filter-value2-${index}`}>
                  Value 2
                </label>
              )}
              <input
                id={`filter-value2-${index}`}
                type="datetime-local"
                className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                value={row.value2}
                onChange={(e) => updateRow(index, { value2: e.target.value })}
              />
            </div>
          )}
        </>
      );
    }

    return (
      <>
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
      </>
    );
  };

  return (
    <CustomModal open={open} onClose={onClose} title="Filters" width="sm:max-w-2xl" footer={null}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3">
          {filterRows.map((row, index) => (
            <div key={index} className="flex items-end gap-2">
              <SelectInput
                name={`filter-field-${index}`}
                label={index === 0 ? 'Field' : undefined}
                options={FILTER_FIELD_OPTIONS}
                value={row.field}
                onValueChange={(v) => handleFieldChange(index, v)}
                placeholder="Select field"
                triggerClassName="w-[150px]"
              />
              {!CATEGORICAL_FIELDS.has(row.field) && (
                <SelectInput
                  name={`filter-operator-${index}`}
                  label={index === 0 ? 'Operator' : undefined}
                  options={
                    DATETIME_FIELDS.has(row.field) ? DATETIME_OPERATOR_OPTIONS : OPERATOR_OPTIONS
                  }
                  value={row.operator}
                  onValueChange={(v) => updateRow(index, { operator: v })}
                  placeholder="Operator"
                  triggerClassName="w-[140px]"
                />
              )}
              {renderValueInput(row, index)}
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

        <div className="flex justify-end gap-2 pt-2">
          <CustomButton
            type="danger"
            onClick={() => {
              onApply([]);
            }}
            disabled={currentFilters.length === 0}
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

export default FilterModal;
