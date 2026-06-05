'use client';

import MetricsContent from '@/components/call-history/metrics/MetricsContent';
import { AppLoader, CustomButton } from '@/components/shared';
import { useGoBack } from '@/hooks/useGoBack';
import { getCallMetricsByCallId } from '@/services/callMetricsService';
import type { CallMetricsDetail } from '@/types/callMetrics';
import { handleApiError } from '@/utils/helpers';
import { ArrowLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

interface CallMetricsDetailPageProps {
  callId: string;
}

const CallMetricsDetailPage: React.FC<CallMetricsDetailPageProps> = ({ callId }) => {
  const goBack = useGoBack('/call-history');
  const [detail, setDetail] = useState<CallMetricsDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    getCallMetricsByCallId(callId, { signal: controller.signal })
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((error) => {
        // Ignore axios cancel/abort errors — they're expected on fast nav.
        if (cancelled || controller.signal.aborted) return;
        handleApiError(error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [callId]);

  const agentName = detail?.agent_name ?? '';

  const crumbLabel = agentName || (loading ? 'Loading…' : 'Detail');

  return (
    <div className="animate-page flex h-full flex-col gap-5">
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-1.5 text-sm text-muted-foreground"
      >
        <Link href="/call-history" className="transition-colors hover:text-foreground">
          Call History
        </Link>
        <ChevronRight className="size-3.5" aria-hidden />
        <span className="font-medium text-foreground">{crumbLabel}</span>
      </nav>

      <div className="flex items-center gap-2">
        <CustomButton
          type="text"
          size="sm"
          icon={<ArrowLeft className="size-4" />}
          onClick={goBack}
          className="-ml-2 h-8 text-muted-foreground hover:text-foreground"
          aria-label="Back to call metrics"
        />
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {`Metrics${agentName ? ` — ${agentName}` : ''}`}
        </h1>
      </div>

      {loading ? (
        <AppLoader />
      ) : detail ? (
        <MetricsContent metrics={detail} />
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground">No metrics found for this call.</p>
        </div>
      )}
    </div>
  );
};

export default CallMetricsDetailPage;
