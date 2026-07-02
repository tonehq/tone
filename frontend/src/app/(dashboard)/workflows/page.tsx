import { redirect } from 'next/navigation';

// The standalone workflows list is gone — workflows are agent-scoped and live
// under each agent's Workflow tab. Old bookmarks land on the agents list; the
// /workflows/[id] builder route stays live as a deep link from that tab.
export default function WorkflowsPage() {
  redirect('/agents');
}
