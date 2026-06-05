import { redirect } from 'next/navigation';

// Moved into the dedicated Settings area.
export default function OrganizationsRedirect() {
  redirect('/settings/organizations');
}
