'use client';

import { AppLoader } from '@/components/shared';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { CALL_DETAIL_SECTION_KEYS, DEFAULT_CALL_DETAIL_SECTION } from '../callDetailNav';
import { useCallDetail } from '../CallDetailContext';
import CallConfigurationsSection from './CallConfigurationsSection';
import MetricsSection from './MetricsSection';
import TranscriptionRecordingsSection from './TranscriptionRecordingsSection';

interface CallDetailSectionBodyProps {
  section: string;
  basePath: string;
}

const CallDetailSectionBody: React.FC<CallDetailSectionBodyProps> = ({ section, basePath }) => {
  const router = useRouter();
  const { callLog, loading } = useCallDetail();

  const known = CALL_DETAIL_SECTION_KEYS.includes(section);

  // Unknown section → bounce to the default landing tab.
  useEffect(() => {
    if (!known) router.replace(`${basePath}/${DEFAULT_CALL_DETAIL_SECTION}`);
  }, [known, router, basePath]);

  if (!known) return null;
  if (loading) return <AppLoader className="h-full" />;
  if (!callLog) {
    return (
      <div className="flex flex-1 items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">No details found for this call.</p>
      </div>
    );
  }

  switch (section) {
    case 'transcription':
      return <TranscriptionRecordingsSection callLog={callLog} />;
    case 'metrics':
      return <MetricsSection callLog={callLog} />;
    case 'configurations':
      return <CallConfigurationsSection callLog={callLog} />;
    default:
      return null;
  }
};

export default CallDetailSectionBody;
