import { redirect } from 'next/navigation';

/**
 * `/contacts` index — the Contacts section opens on its General (directories)
 * view. Redirect to `/contacts/directories`, the first rail destination.
 */
export default function ContactsIndexPage() {
  redirect('/contacts/directories');
}
