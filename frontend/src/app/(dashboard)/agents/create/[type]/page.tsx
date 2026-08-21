import { redirect } from 'next/navigation';

// New agents start on Setup (Basics + AI stacked; Overview is edit-only).
export default async function CreateAgentIndex({ params }: { params: Promise<{ type: string }> }) {
  const { type } = await params;
  redirect(`/agents/create/${type}/setup`);
}
