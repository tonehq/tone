'use client';

import { ArrowLeft } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';

import ContactDirectoryRail from '@/components/contacts/ContactDirectoryRail';
import { CustomButton } from '@/components/shared';
import { cn } from '@/lib/utils';

/**
 * Two-pane responsive shell for the Contacts master-detail experience.
 *
 * WHAT: renders the persistent `ContactDirectoryRail` alongside a right-pane
 * slot (`children` — the detail route or the "select a directory" placeholder).
 * At ≥1024px both panes are visible side-by-side. Below 1024px it collapses to
 * a single pane: the rail shows when no directory is selected, and the detail
 * (with a "Back to directories" control) shows when one is. Selecting a rail
 * item navigates to `/contacts/directories/[id]`, which is the single source of
 * truth for the active directory — the rail stays mounted so its scroll +
 * selection survive back-navigation.
 *
 * WHEN: rendered by `contacts/directories/layout.tsx` to wrap every
 * `/contacts/directories/*` route.
 */
export interface ContactsMasterDetailProps {
  children: React.ReactNode;
}

export default function ContactsMasterDetail({ children }: ContactsMasterDetailProps) {
  const router = useRouter();
  const params = useParams<{ directoryId?: string }>();
  const activeDirectoryId = params?.directoryId ?? null;

  const handleSelect = (directoryId: string) => {
    router.push(`/contacts/directories/${directoryId}`);
  };

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 overflow-hidden bg-card">
      {/* Left rail — full width on mobile until a directory is selected. */}
      <aside
        className={cn(
          'min-h-0 shrink-0 border-border lg:flex lg:w-[300px] lg:border-r',
          activeDirectoryId ? 'hidden lg:flex' : 'flex w-full',
        )}
      >
        <ContactDirectoryRail activeDirectoryId={activeDirectoryId} onSelect={handleSelect} />
      </aside>

      {/* Right pane — hidden on mobile until a directory is selected. */}
      <section
        className={cn(
          'min-h-0 min-w-0 flex-1 flex-col',
          activeDirectoryId ? 'flex' : 'hidden lg:flex',
        )}
      >
        {activeDirectoryId && (
          <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
            <CustomButton
              type="text"
              size="sm"
              icon={<ArrowLeft className="size-4" />}
              onClick={() => router.push('/contacts/directories')}
            >
              Directories
            </CustomButton>
          </div>
        )}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</div>
      </section>
    </div>
  );
}
