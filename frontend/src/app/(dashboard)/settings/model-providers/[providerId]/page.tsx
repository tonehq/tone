import { redirect } from 'next/navigation';

// Detail pages are now scoped to (provider, service_type). Land on the
// listing instead of trying to guess which kind the user meant.
const Page = () => {
  redirect('/settings/model-providers');
};

export default Page;
