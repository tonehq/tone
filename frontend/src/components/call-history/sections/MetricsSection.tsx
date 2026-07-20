'use client';

import MetricsContent from '@/components/call-history/metrics/MetricsContent';
import { getCallToolExecutions } from '@/services/callLogService';
import type { CallLogRow, ToolExecution } from '@/types/callLog';
import { handleApiError } from '@/utils/helpers';
import React, { useEffect, useState } from 'react';

interface MetricsSectionProps {
  callLog: CallLogRow;
}

const MetricsSection: React.FC<MetricsSectionProps> = ({ callLog }) => {
  // Fetch the authoritative typed tool_executions list — `callLog.tool_calls`
  // is a legacy `calls.metadata["tool_calls"]` blob that is often empty on
  // recent calls, so relying on it would silently show 0s in the per-turn
  // Tool Calls column.
  const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
  useEffect(() => {
    let cancelled = false;
    getCallToolExecutions(callLog.id)
      .then((data) => {
        if (!cancelled) setToolExecutions(data);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [callLog.id]);

  const header = (
    <div className="mb-5">
      <h3 className="text-sm font-medium text-foreground">Performance</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Latency, tokens, and processor breakdown for this call.
      </p>
    </div>
  );

  if (!callLog.metrics) {
    return (
      <div className="flex h-full flex-col">
        {header}
        <div className="flex flex-1 items-center justify-center py-12">
          <p className="text-sm text-muted-foreground">No metrics recorded for this call.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {header}
      <MetricsContent metrics={callLog.metrics} toolExecutions={toolExecutions} />
    </div>
  );
};

export default MetricsSection;
