'use client';

import scheduledCallsAtom, {
  cancelScheduledCallAtom,
  cancelScheduledCallsAtom,
  fetchScheduledCalls,
} from '@/atoms/OutboundCallsAtom';
import NewOutboundCallModal from '@/components/outbound-calls/NewOutboundCallModal';
import ScheduledCallStatusChip from '@/components/scheduled-calls/ScheduledCallStatusChip';
import type { CustomTableColumn } from '@/components/shared';
import { CustomButton, CustomModal, CustomTable, CustomTooltip } from '@/components/shared';
import { Checkbox } from '@/components/ui/checkbox';
import type { ScheduledCallRow, ScheduledCallStatus } from '@/types/outboundCall';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtomValue, useSetAtom } from 'jotai';
import { Ban, PhoneForwarded, PhoneOutgoing } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

const PAGE_SIZE = 10;
const POLL_MS = 5000;

const TERMINAL: ScheduledCallStatus[] = ['completed', 'busy', 'no_answer', 'failed', 'canceled'];
// Only a still-queued call is cancelable; once the worker is dialing ('processing')
// it owns the call, so the backend rejects a cancel then (409).
const CANCELABLE: ScheduledCallStatus[] = ['scheduled'];

const isTerminal = (s: ScheduledCallStatus | null) => !!s && TERMINAL.includes(s);
const isCancelable = (s: ScheduledCallStatus | null) => !!s && CANCELABLE.includes(s);

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

export default function ScheduledCallsPage() {
  const { rows, total, loading } = useAtomValue(scheduledCallsAtom);
  const fetchCalls = useSetAtom(fetchScheduledCalls);
  const cancelCall = useSetAtom(cancelScheduledCallAtom);
  const cancelCalls = useSetAtom(cancelScheduledCallsAtom);

  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<ScheduledCallRow | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkCancelling, setBulkCancelling] = useState(false);
  const pageRef = useRef(page);
  pageRef.current = page;

  const load = useCallback(
    async (pageNo: number, silent = false) => {
      try {
        await fetchCalls({
          params: { page_no: pageNo, page_size: PAGE_SIZE, sort_order: 'desc' },
          silent,
        });
      } catch (err) {
        handleApiError(err);
      }
    },
    [fetchCalls],
  );

  // First load (per page) shows the skeleton; the refreshes below are silent.
  useEffect(() => {
    load(page);
  }, [page, load]);

  // Poll while any visible scheduled call is still pending/in flight — silent so the
  // table updates in place without flashing the skeleton on every refresh.
  const hasLive = rows.some((r) => !isTerminal(r.status));
  useEffect(() => {
    if (!hasLive) return;
    const id = setInterval(() => load(pageRef.current, true), POLL_MS);
    return () => clearInterval(id);
  }, [hasLive, load]);

  // Drop any selected ids that are no longer cancelable (e.g. dispatched during a poll).
  useEffect(() => {
    const cancelable = new Set(rows.filter((r) => isCancelable(r.status)).map((r) => r.id));
    setSelectedIds((prev) => {
      const next = new Set([...prev].filter((id) => cancelable.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [rows]);

  const cancelableIds = rows.filter((r) => isCancelable(r.status)).map((r) => r.id);
  const allSelected = cancelableIds.length > 0 && cancelableIds.every((id) => selectedIds.has(id));
  const someSelected = cancelableIds.some((id) => selectedIds.has(id));

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (cancelableIds.every((id) => prev.has(id)) && cancelableIds.length > 0) {
        const next = new Set(prev);
        cancelableIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set([...prev, ...cancelableIds]);
    });
  }, [cancelableIds]);

  const toggleOne = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const confirmCancel = useCallback(async () => {
    if (!cancelTarget) return;
    setCancelling(true);
    try {
      await cancelCall(cancelTarget.id);
      showToast.success('Scheduled call canceled');
      setCancelTarget(null);
      load(pageRef.current, true);
    } catch (err) {
      handleApiError(err);
    } finally {
      setCancelling(false);
    }
  }, [cancelTarget, cancelCall, load]);

  const confirmBulkCancel = useCallback(async () => {
    const ids = [...selectedIds];
    if (!ids.length) return;
    setBulkCancelling(true);
    try {
      const res = await cancelCalls(ids);
      showToast.success(
        `${res.canceled} call${res.canceled === 1 ? '' : 's'} canceled`,
        res.skipped?.length ? `${res.skipped.length} could not be canceled` : undefined,
      );
      setSelectedIds(new Set());
      setBulkOpen(false);
      load(pageRef.current, true);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBulkCancelling(false);
    }
  }, [selectedIds, cancelCalls, load]);

  const columns: CustomTableColumn<ScheduledCallRow>[] = [
    {
      key: 'select',
      width: 'w-10',
      title: (
        <Checkbox
          aria-label="Select all cancelable calls"
          checked={allSelected ? true : someSelected ? 'indeterminate' : false}
          onCheckedChange={toggleAll}
          disabled={cancelableIds.length === 0}
        />
      ),
      render: (_v, record) =>
        isCancelable(record.status) ? (
          <Checkbox
            aria-label={`Select ${record.to_number ?? 'call'}`}
            checked={selectedIds.has(record.id)}
            onCheckedChange={() => toggleOne(record.id)}
          />
        ) : null,
    },
    {
      key: 'to_number',
      title: 'To',
      dataIndex: 'to_number',
      render: (value) => (
        <span className="font-medium tabular-nums">{(value as string) ?? '—'}</span>
      ),
    },
    {
      key: 'agent_name',
      title: 'Agent',
      dataIndex: 'agent_name',
      render: (value) => <span>{(value as string) ?? '—'}</span>,
    },
    {
      key: 'status',
      title: 'Status',
      render: (_v, record) => <ScheduledCallStatusChip status={record.status} />,
    },
    {
      key: 'scheduled_at',
      title: 'Scheduled for',
      render: (_v, record) => (
        <span className="tabular-nums">{formatDateTime(record.scheduled_at)}</span>
      ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      render: (_v, record) => (
        <div className="flex items-center justify-end gap-1">
          {record.call_id && (
            <CustomTooltip content="View call">
              <Link href={`/call-history/${record.call_id}`}>
                <CustomButton type="text" icon={<PhoneForwarded className="size-3.5" />} />
              </Link>
            </CustomTooltip>
          )}
          {isCancelable(record.status) && (
            <CustomTooltip content="Cancel">
              <CustomButton
                type="danger"
                icon={<Ban className="size-3.5" />}
                onClick={() => setCancelTarget(record)}
              />
            </CustomTooltip>
          )}
        </div>
      ),
    },
  ];

  const selectedCount = selectedIds.size;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Scheduled Calls</h1>
          <p className="text-sm text-muted-foreground">
            Outbound calls queued to dial at a future time. Connected calls appear in Call History.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<PhoneOutgoing className="size-4" />}
          onClick={() => setCreateOpen(true)}
        >
          Schedule Call
        </CustomButton>
      </div>

      {selectedCount > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-4 py-2.5">
          <span className="text-sm font-medium">{selectedCount} selected</span>
          <div className="flex items-center gap-2">
            <CustomButton type="text" onClick={() => setSelectedIds(new Set())}>
              Clear
            </CustomButton>
            <CustomButton
              type="danger"
              icon={<Ban className="size-3.5" />}
              onClick={() => setBulkOpen(true)}
            >
              Cancel {selectedCount}
            </CustomButton>
          </div>
        </div>
      )}

      <CustomTable
        columns={columns}
        dataSource={rows}
        rowKey="id"
        loading={loading}
        pagination={{ current: page, pageSize: PAGE_SIZE, total, onChange: setPage }}
        emptyState={
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <PhoneOutgoing className="size-8 text-muted-foreground/60" aria-hidden />
            <div>
              <p className="font-medium">No scheduled calls</p>
              <p className="text-sm text-muted-foreground">
                Queue a call to dial at a future time.
              </p>
            </div>
            <CustomButton type="primary" onClick={() => setCreateOpen(true)}>
              Schedule Call
            </CustomButton>
          </div>
        }
      />

      <NewOutboundCallModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onScheduled={() => {
          if (page === 1) load(1, true);
          else setPage(1);
        }}
      />

      <CustomModal
        open={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title="Cancel this scheduled call?"
        description="It will not be dialed."
        confirmText="Cancel call"
        confirmType="danger"
        confirmLoading={cancelling}
        cancelText="Keep"
        onConfirm={confirmCancel}
      />

      <CustomModal
        open={bulkOpen}
        onClose={() => setBulkOpen(false)}
        title={`Cancel ${selectedCount} scheduled call${selectedCount === 1 ? '' : 's'}?`}
        description="The selected calls will not be dialed. Already-dispatched calls are skipped."
        confirmText={`Cancel ${selectedCount}`}
        confirmType="danger"
        confirmLoading={bulkCancelling}
        cancelText="Keep"
        onConfirm={confirmBulkCancel}
      />
    </div>
  );
}
