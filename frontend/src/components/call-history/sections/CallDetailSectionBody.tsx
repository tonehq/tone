'use client';

import { AppLoader } from '@/components/shared';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { CALL_DETAIL_SECTION_KEYS, DEFAULT_CALL_DETAIL_SECTION } from '../callDetailNav';
import { useCallDetail } from '../CallDetailContext';
import CallConfigurationsSection from './CallConfigurationsSection';
import ConsolidatedSection from './ConsolidatedSection';
import MetricsSection from './MetricsSection';
import ToolsMcpSection from './ToolsMcpSection';
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
  // `min-h-0` overrides AppLoader's default `min-h-screen` so it centers
  // within the tab body, not at viewport mid-point (which would sit below
  // the visible area once the sticky summary card consumes space above).
  if (loading) return <AppLoader className="min-h-0 h-full" />;
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
    case 'consolidated':
      return <ConsolidatedSection callLog={callLog} />;
    case 'metrics':
      return <MetricsSection callLog={callLog} />;
    case 'tools-mcp':
      return <ToolsMcpSection callLog={callLog} />;
    case 'configurations':
      return <CallConfigurationsSection callLog={callLog} />;
    default:
      return null;
  }
};

export default CallDetailSectionBody;
