'use client';

import MetricsContent from '@/components/call-history/metrics/MetricsContent';
import type { CallLogRow } from '@/types/callLog';
import React from 'react';

interface MetricsSectionProps {
  callLog: CallLogRow;
}

const MetricsSection: React.FC<MetricsSectionProps> = ({ callLog }) => {
  if (!callLog.metrics) {
    return (
      <div className="flex flex-1 items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">No metrics recorded for this call.</p>
      </div>
    );
  }

  return <MetricsContent metrics={callLog.metrics} />;
};

export default MetricsSection;
