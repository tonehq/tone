'use client';

import MetricsContent from '@/components/call-history/metrics/MetricsContent';
import { CustomButton, CustomTooltip } from '@/components/shared';
import type { CallLogRow } from '@/types/callLog';
import { buildGrafanaLogsUrl, isGrafanaConfigured } from '@/utils/grafana';
import { ScrollText } from 'lucide-react';
import React from 'react';

interface MetricsSectionProps {
  callLog: CallLogRow;
}

const MetricsSection: React.FC<MetricsSectionProps> = ({ callLog }) => {
  const grafanaEnabled = isGrafanaConfigured();
  const hasTrace = !!callLog.trace_id;

  const openLogs = () => {
    const url = buildGrafanaLogsUrl(callLog);
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  };

  const header = grafanaEnabled && (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 className="text-sm font-medium text-foreground">Performance</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Latency, tokens, and processor breakdown for this call.
        </p>
      </div>
      <CustomTooltip content={hasTrace ? 'View logs in Grafana' : 'No trace id for this call'}>
        <span>
          <CustomButton
            type="default"
            size="sm"
            icon={<ScrollText className="size-3.5" />}
            disabled={!hasTrace}
            onClick={openLogs}
          >
            View logs
          </CustomButton>
        </span>
      </CustomTooltip>
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
      <MetricsContent metrics={callLog.metrics} />
    </div>
  );
};

export default MetricsSection;
