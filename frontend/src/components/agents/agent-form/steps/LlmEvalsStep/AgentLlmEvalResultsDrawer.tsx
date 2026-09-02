import { CustomDrawer } from '@/components/shared';
import { useAgentLlmEvalRunDetail } from '@/lib/api/agentLlmEvals';

import AgentPromptPanel from './AgentPromptPanel';
import ScoredScenarioRow from './ScoredScenarioRow';
import SummaryCell from './SummaryCell';

export default function AgentLlmEvalResultsDrawer({
  open,
  onClose,
  agentId,
  runId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  runId: string | null;
}) {
  const detailQuery = useAgentLlmEvalRunDetail(open ? agentId : null, open ? runId : null);
  const summary = detailQuery.data?.summary;
  const totals = summary?.summary as Record<string, number> | undefined;

  // Every scenario in a run scores against the SAME snapshotted agent
  // config, so the system prompt is identical row-to-row. Pull it once from
  // the first scored scenario and render it in a single collapsible panel
  // at the top of the drawer — the per-row "System prompt at run time"
  // section is removed to avoid duplicating the same text N times.
  const scenarios = detailQuery.data?.scenarios ?? [];
  const sharedSystemPrompt = scenarios.find((s) => s.system_prompt)?.system_prompt ?? null;

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={summary ? `LLM eval run #${summary.run_number}` : 'LLM eval run'}
      description="Every scored scenario in this batch."
      width="w-[900px] sm:max-w-[95vw]"
    >
      <div className="flex flex-col gap-4">
        {detailQuery.isLoading && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            Loading run…
          </div>
        )}
        {summary && totals && (
          <section className="rounded-lg border border-border/60 bg-card p-3">
            <div className="grid grid-cols-3 gap-3 text-[12.5px] sm:grid-cols-5">
              <SummaryCell label="Score" value={`${totals.pass ?? 0} / ${totals.total ?? 0}`} />
              <SummaryCell
                label="Pass rate"
                value={`${Math.round(((totals.pass_rate ?? 0) as number) * 100)}%`}
              />
              <SummaryCell label="Partial" value={String(totals.partial ?? 0)} />
              <SummaryCell label="Fail" value={String(totals.fail ?? 0)} />
              <SummaryCell label="Judge" value={summary.judge_model ?? '—'} />
            </div>
          </section>
        )}
        {sharedSystemPrompt && <AgentPromptPanel prompt={sharedSystemPrompt} />}
        {detailQuery.data?.scenarios.map((s) => (
          <ScoredScenarioRow key={s.id} scored={s} />
        ))}
        {detailQuery.data && detailQuery.data.scenarios.length === 0 && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            No scored scenarios yet.
          </div>
        )}
      </div>
    </CustomDrawer>
  );
}
