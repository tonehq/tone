import { DEFAULT_CALL_DETAIL_SECTION } from '@/components/call-history/callDetailNav';
import { redirect } from 'next/navigation';

// Opening a call lands on the default tab (Transcription & Recordings).
// Preserve `?from=<origin>` so a call opened from an agent's Call History tab
// keeps its back-target through this redirect.
export default async function CallDetailIndex({
  params,
  searchParams,
}: {
  params: Promise<{ callId: string }>;
  searchParams: Promise<{ from?: string }>;
}) {
  const { callId } = await params;
  const { from } = await searchParams;
  const qs = from ? `?from=${encodeURIComponent(from)}` : '';
  redirect(`/call-history/${callId}/${DEFAULT_CALL_DETAIL_SECTION}${qs}`);
}
