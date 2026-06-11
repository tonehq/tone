'use client';

import CallDetailShell from '@/components/call-history/CallDetailShell';
import { useParams } from 'next/navigation';

export default function CallDetailLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const callId = params?.callId as string;

  return <CallDetailShell callId={callId}>{children}</CallDetailShell>;
}
