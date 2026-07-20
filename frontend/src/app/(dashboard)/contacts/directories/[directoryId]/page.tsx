'use client';

import { useParams } from 'next/navigation';

import DirectoryDetailHeader from '@/components/contacts/DirectoryDetailHeader';
// PIN: built by another agent — prop `{ directoryId: string }`. If missing at
// build time, that's an integration gap, not an error in this file.
import DirectoryContactsSection from '@/components/contacts/general/DirectoryContactsSection';

/**
 * General pane host for a directory: the detail header (General tab active) plus
 * the contacts section (table + add + sync).
 */
export default function DirectoryGeneralPage() {
  const params = useParams<{ directoryId: string }>();
  const directoryId = params.directoryId;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <DirectoryDetailHeader directoryId={directoryId} />
      <div className="flex min-h-0 flex-1 flex-col p-6">
        <DirectoryContactsSection directoryId={directoryId} />
      </div>
    </div>
  );
}
