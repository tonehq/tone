import { ChevronDown, ChevronRight, Folder as FolderIcon, Wrench } from 'lucide-react';
import { useState } from 'react';

import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import { CustomButton } from '@/components/shared';
import type { AgentLlmEvalScoredScenario } from '@/types/agentLlmEval';

import VerdictChip from './VerdictChip';

export default function ScoredScenarioRow({ scored }: { scored: AgentLlmEvalScoredScenario }) {
  const [expanded, setExpanded] = useState(false);
  // Per-scenario "system prompt at run time" section was removed — the
  // prompt is identical across every scored row in a run, so it lives once
  // at the top of the drawer (see ``AgentPromptPanel``).
  return (
    <div className="rounded-md border border-border/60 bg-card">
      <CustomButton
        type="text"
        fullWidth
        onClick={() => setExpanded((v) => !v)}
        className="flex h-auto items-start justify-start gap-2 rounded-none px-3 py-2 text-left hover:bg-transparent"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictChip verdict={scored.verdict} />
            <span className="text-[11px] text-muted-foreground">{scored.scenario_key}</span>
            {scored.folder && (
              <span
                title={`Folder: ${scored.folder}`}
                className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border"
              >
                <FolderIcon className="size-2.5" />
                {scored.folder}
              </span>
            )}
            {scored.latency_ms != null && (
              <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
                {scored.latency_ms}ms
              </span>
            )}
          </div>
          <div className="mt-1 line-clamp-2 text-[13px] font-medium text-foreground">
            {scored.prompt}
          </div>
        </div>
      </CustomButton>
      {expanded && (
        <div className="grid grid-cols-1 gap-3 border-t border-border/60 px-3 py-3 text-[12.5px] md:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Expected
            </div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.expected_answer ?? '—'}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Actual</div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.actual_answer ?? '—'}
            </div>
          </div>
          {scored.judge_reasoning && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Judge reasoning
              </div>
              <div className="mt-1 whitespace-pre-wrap text-foreground">
                {formatIngestionError(scored.judge_reasoning) ?? scored.judge_reasoning}
              </div>
            </div>
          )}
          {/* Tool call intents (Phase 2). Only surfaces when the executor
              actually captured tool_calls — no-tool scenarios stay quiet.
              The deterministic ``tool_selection`` metric verdict + reason
              live under Metrics + Judge reasoning above, so this section
              is inspection-only ("what did the LLM ask to call?"). */}
          {scored.tools_called && scored.tools_called.length > 0 && (
            <div className="md:col-span-2">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                <Wrench className="size-3" />
                Tool call intents
              </div>
              <div className="mt-1 flex flex-col gap-2">
                {scored.tools_called.map((intent, i) => (
                  <div
                    // Tool call intents are ordered + repeatable (same tool
                    // may be called twice), so index-in-list is the stable
                    // React key; ``name`` alone would collide.
                    key={`${intent.name}-${i}`}
                    className="rounded border border-border/60 bg-muted/40 px-2 py-1.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11.5px] font-medium text-foreground">
                        {intent.name}
                      </span>
                    </div>
                    {intent.arguments && Object.keys(intent.arguments).length > 0 && (
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all text-[11px] text-muted-foreground">
                        {JSON.stringify(intent.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {scored.metric_scores && Object.keys(scored.metric_scores).length > 0 && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Metrics
              </div>
              <div className="mt-1 flex flex-wrap gap-3">
                {Object.entries(scored.metric_scores).map(([name, entry]) => (
                  <div key={name} className="rounded bg-muted px-2 py-1 text-[11px]">
                    <span className="font-medium text-foreground">{name}</span>{' '}
                    <span className="tabular-nums text-muted-foreground">
                      {entry?.score != null ? entry.score.toFixed(2) : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(scored.answer_error || scored.judge_error) && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Errors
              </div>
              {scored.answer_error && (
                <div className="mt-1 text-destructive">
                  Answer: {formatIngestionError(scored.answer_error) ?? scored.answer_error}
                </div>
              )}
              {scored.judge_error && (
                <div className="mt-1 text-destructive">
                  Judge: {formatIngestionError(scored.judge_error) ?? scored.judge_error}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
