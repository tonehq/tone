import { DEFAULT_CALL_DETAIL_SECTION } from '@/components/call-history/callDetailNav';
import { redirect } from 'next/navigation';

// Opening a call lands on the default tab (Transcription & Recordings).
export default async function CallDetailIndex({ params }: { params: Promise<{ callId: string }> }) {
  const { callId } = await params;
  redirect(`/call-history/${callId}/${DEFAULT_CALL_DETAIL_SECTION}`);
}
