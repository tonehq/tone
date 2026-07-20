import ContactsMasterDetail from '@/components/contacts/ContactsMasterDetail';

/**
 * Master-detail shell for the Contact Directories (General) view.
 *
 * Wraps every `/contacts/directories/*` route with the persistent left rail
 * (directory list) and a right-pane slot (`children`). The rail stays mounted
 * across detail navigation so its scroll position and selection are preserved.
 * This shell lives one level down under the focused Contacts section rail
 * (contacts/layout.tsx).
 */
export default function ContactsDirectoriesLayout({ children }: { children: React.ReactNode }) {
  return <ContactsMasterDetail>{children}</ContactsMasterDetail>;
}
