import { redirect } from 'next/navigation';

// New agents start on Basics (there's nothing to summarise yet).
export default async function CreateAgentIndex({ params }: { params: Promise<{ type: string }> }) {
  const { type } = await params;
  redirect(`/agents/create/${type}/basics`);
}
