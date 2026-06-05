'use client';

import CallMetricsDetailPage from '@/components/call-metrics/CallMetricsDetailPage';
import { useParams } from 'next/navigation';

export default function CallMetricsDetailRoute() {
  const params = useParams();
  const callId = params?.callId as string;

  return <CallMetricsDetailPage callId={callId} />;
}
