import { redirect } from 'next/navigation';

// Opening an agent lands on its Overview.
export default async function EditAgentIndex({
  params,
}: {
  params: Promise<{ type: string; id: string }>;
}) {
  const { type, id } = await params;
  redirect(`/agents/edit/${type}/${id}/overview`);
}
