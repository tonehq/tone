'use client';

import callLogsAtom, { fetchCallLogs } from '@/atoms/CallLogAtom';
import { CustomButton, CustomTable } from '@/components/shared';
import type { CallLogFilterParam, CallLogQueryParams, CallLogRow } from '@/types/callLog';
import type { CustomTableColumn } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import { ArrowUpDown, CalendarDays, Filter, Phone, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';

import CallDetailDrawer from './CallDetailDrawer';
import FilterModal from './FilterSortModal';
import SortModal from './SortModal';

const formatTimestamp = (ts: number | null): string => {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString();
};

const formatDuration = (seconds: number | null): string => {
  if (seconds == null) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

const CallHistory: React.FC = () => {
  const [data] = useAtom(callLogsAtom);
  const [, doFetchCallLogs] = useAtom(fetchCallLogs);

  const [pageNo, setPageNo] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [startDateTime, setStartDateTime] = useState('');
  const [endDateTime, setEndDateTime] = useState('');
  const [filters, setFilters] = useState<CallLogFilterParam[]>([]);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [refreshKey, setRefreshKey] = useState(0);
  const [dateApplied, setDateApplied] = useState(false);

  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [sortModalOpen, setSortModalOpen] = useState(false);
  const [selectedCallLog, setSelectedCallLog] = useState<CallLogRow | null>(null);

  // Snapshot date values on each fetch trigger so they stay stable in the dep array
  const startRef = useRef(startDateTime);
  const endRef = useRef(endDateTime);

  useEffect(() => {
    startRef.current = startDateTime;
    endRef.current = endDateTime;
  }, [startDateTime, endDateTime]);

  // Single effect for all fetches
  useEffect(() => {
    const fetchData = async () => {
      try {
        const params: CallLogQueryParams = {
          page_no: pageNo,
          page_size: pageSize,
        };

        if (startRef.current) {
          params.start_date_time = Math.floor(new Date(startRef.current).getTime() / 1000);
        }
        if (endRef.current) {
          params.end_date_time = Math.floor(new Date(endRef.current).getTime() / 1000);
        }
        if (filters.length > 0) {
          params.filters = filters;
        }
        if (sortBy) {
          params.sort_by = sortBy;
          params.sort_order = sortOrder;
        }

        await doFetchCallLogs(params);
      } catch (err) {
        handleApiError(err);
      }
    };

    fetchData();
  }, [pageNo, pageSize, filters, sortBy, sortOrder, refreshKey, doFetchCallLogs]);

  const handleDateFilter = useCallback(() => {
    if (dateApplied) {
      setStartDateTime('');
      setEndDateTime('');
      setDateApplied(false);
    } else {
      setDateApplied(true);
    }
    setPageNo(1);
    setRefreshKey((k) => k + 1);
  }, [dateApplied]);

  const handleApplyFilters = useCallback((newFilters: CallLogFilterParam[]) => {
    setFilters(newFilters);
    setPageNo(1);
    setFilterModalOpen(false);
  }, []);

  const handleApplySort = useCallback((newSortBy?: string, newSortOrder?: 'asc' | 'desc') => {
    setSortBy(newSortBy);
    setSortOrder(newSortOrder ?? 'desc');
    setPageNo(1);
    setSortModalOpen(false);
  }, []);

  const columns: CustomTableColumn<CallLogRow>[] = [
    {
      key: 'sno',
      title: 'S.No',
      width: '40px',
      render: (_value, _record, index) => (pageNo - 1) * pageSize + index + 1,
    },
    {
      key: 'agent_name',
      title: 'Agent',
      dataIndex: 'agent_name',
      render: (_value, record) => (
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium">{record.agent_name || '-'}</span>
          <AgentTypeBadge agentType={record.agent_type} />
        </div>
      ),
    },
    {
      key: 'started_at',
      title: 'Call Start At',
      dataIndex: 'started_at',
      render: (value) => formatTimestamp(value as number | null),
    },
    {
      key: 'ended_at',
      title: 'Call End At',
      dataIndex: 'ended_at',
      render: (value) => formatTimestamp(value as number | null),
    },
    {
      key: 'duration_seconds',
      title: 'Call Duration',
      dataIndex: 'duration_seconds',
      render: (value) => formatDuration(value as number | null),
    },
    {
      key: 'from_number',
      title: 'Call From Number',
      dataIndex: 'from_number',
      render: (value) => (value as string) || '-',
    },
    {
      key: 'to_number',
      title: 'Call To Number',
      dataIndex: 'to_number',
      render: (value) => (value as string) || '-',
    },
  ];

  return (
    <div className="flex h-full flex-col p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-foreground">Call History</h1>
      </div>

      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <CalendarDays className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              id="start-datetime"
              type="datetime-local"
              value={startDateTime}
              onChange={(e) => setStartDateTime(e.target.value)}
              placeholder="Start date"
              className={`h-9 rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 ${startDateTime ? 'text-foreground' : 'text-muted-foreground'}`}
            />
          </div>
          <span className="text-sm text-muted-foreground">to</span>
          <div className="relative">
            <CalendarDays className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              id="end-datetime"
              type="datetime-local"
              value={endDateTime}
              onChange={(e) => setEndDateTime(e.target.value)}
              placeholder="End date"
              className={`h-9 rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground hover:border-ring focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 ${endDateTime ? 'text-foreground' : 'text-muted-foreground'}`}
            />
          </div>
          <CustomButton
            type={dateApplied ? 'danger' : 'primary'}
            size="sm"
            icon={dateApplied ? <X className="size-4" /> : undefined}
            onClick={handleDateFilter}
          >
            {dateApplied ? 'Clear Date Filter' : 'Apply Date Filter'}
          </CustomButton>
        </div>
        <div className="flex items-end gap-2">
          <CustomButton
            type={filters.length > 0 ? 'primary' : 'default'}
            size="sm"
            icon={<Filter className="size-4" />}
            onClick={() => setFilterModalOpen(true)}
          >
            Filter
          </CustomButton>
          <CustomButton
            type={sortBy ? 'primary' : 'default'}
            size="sm"
            icon={<ArrowUpDown className="size-4" />}
            onClick={() => setSortModalOpen(true)}
          >
            Sort
          </CustomButton>
        </div>
      </div>

      <CustomTable
        columns={columns}
        dataSource={data.callLogs}
        rowKey="id"
        loading={data.loading}
        onRowClick={(record) => setSelectedCallLog(record)}
        pagination={{
          current: pageNo,
          pageSize: pageSize,
          total: data.total,
          onChange: (page, size) => {
            setPageNo(page);
            setPageSize(size);
          },
        }}
        emptyState={
          <div className="flex flex-col items-center gap-3 py-12">
            <Phone className="size-12 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No call logs found</p>
          </div>
        }
      />

      <FilterModal
        open={filterModalOpen}
        onClose={() => setFilterModalOpen(false)}
        onApply={handleApplyFilters}
        currentFilters={filters}
      />

      <SortModal
        open={sortModalOpen}
        onClose={() => setSortModalOpen(false)}
        onApply={handleApplySort}
        currentSortBy={sortBy}
        currentSortOrder={sortOrder}
      />

      <CallDetailDrawer
        open={!!selectedCallLog}
        onClose={() => setSelectedCallLog(null)}
        callLog={selectedCallLog}
      />
    </div>
  );
};

export default CallHistory;
