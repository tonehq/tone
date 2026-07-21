'use client';

import ContactSchemaSection from '@/components/contacts/schema/ContactSchemaSection';

/**
 * `/contacts/schema` — the org-level reusable contact-schema library, independent of any
 * directory. Schemas defined here are shared across directories (a directory picks one as
 * its default via the directory form). Lives inside the focused Contacts section rail under
 * "Schema".
 */
export default function ContactsSchemaPage() {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-col gap-1 border-b border-border px-6 py-5">
        <h1 className="text-xl font-semibold text-foreground">Schemas</h1>
        <p className="text-sm text-muted-foreground">
          Reusable contact schemas — define fields once and share them across directories.
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col p-6">
        <ContactSchemaSection />
      </div>
    </div>
  );
}
