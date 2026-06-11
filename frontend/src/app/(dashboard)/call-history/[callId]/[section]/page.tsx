'use client';

import CallDetailSectionBody from '@/components/call-history/sections/CallDetailSectionBody';
import { useParams } from 'next/navigation';

export default function CallDetailSectionRoute() {
  const params = useParams();
  const callId = params?.callId as string;
  const section = params?.section as string;

  return <CallDetailSectionBody section={section} basePath={`/call-history/${callId}`} />;
}
