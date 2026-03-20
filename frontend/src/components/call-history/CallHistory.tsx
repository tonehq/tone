'use client';

import callLogsAtom, { fetchCallLogs } from '@/atoms/CallLogAtom';
import { CustomButton, CustomTable } from '@/components/shared';
import type { CallLogFilterParam, CallLogQueryParams, CallLogRow } from '@/types/callLog';
import type { CustomTableColumn } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { useAtom } from 'jotai';
import { Filter, Phone } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';

import FilterSortModal from './FilterSortModal';
import TranscriptionModal from './TranscriptionModal';

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

  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [transcriptRow, setTranscriptRow] = useState<CallLogRow | null>(null);

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
          params.filters = JSON.stringify(filters);
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
    setPageNo(1);
    setRefreshKey((k) => k + 1);
  }, []);

  const handleApplyFilters = useCallback(
    (newFilters: CallLogFilterParam[], newSortBy?: string, newSortOrder?: 'asc' | 'desc') => {
      setFilters(newFilters);
      setSortBy(newSortBy);
      setSortOrder(newSortOrder ?? 'desc');
      setPageNo(1);
      setFilterModalOpen(false);
    },
    [],
  );

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
      key: 'transcript',
      title: 'Call Transcription',
      render: (_value, record) => {
        if (!record.transcript || record.transcript.length === 0) return '-';
        return (
          <CustomButton type="link" size="sm" onClick={() => setTranscriptRow(record)}>
            Check Transcription
          </CustomButton>
        );
      },
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
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="start-datetime" className="text-sm text-muted-foreground">
              Start Date/Time
            </label>
            <input
              id="start-datetime"
              type="datetime-local"
              value={startDateTime}
              onChange={(e) => setStartDateTime(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="end-datetime" className="text-sm text-muted-foreground">
              End Date/Time
            </label>
            <input
              id="end-datetime"
              type="datetime-local"
              value={endDateTime}
              onChange={(e) => setEndDateTime(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
            />
          </div>
          <CustomButton type="primary" size="sm" onClick={handleDateFilter}>
            Apply Date Filter
          </CustomButton>
        </div>
        <CustomButton
          type="default"
          size="sm"
          icon={<Filter className="size-4" />}
          onClick={() => setFilterModalOpen(true)}
        >
          Filters & Sort
        </CustomButton>
      </div>

      <CustomTable
        columns={columns}
        dataSource={data.callLogs}
        rowKey="id"
        loading={data.loading}
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

      <FilterSortModal
        open={filterModalOpen}
        onClose={() => setFilterModalOpen(false)}
        onApply={handleApplyFilters}
        currentFilters={filters}
        currentSortBy={sortBy}
        currentSortOrder={sortOrder}
      />

      <TranscriptionModal
        open={!!transcriptRow}
        onClose={() => setTranscriptRow(null)}
        transcript={transcriptRow?.transcript ?? null}
        agentName={transcriptRow?.agent_name ?? ''}
      />
    </div>
  );
};

export default CallHistory;
