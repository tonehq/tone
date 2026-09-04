import { Pencil, Play, Trash2, Wrench } from 'lucide-react';
import { useMemo } from 'react';

import { CustomButton } from '@/components/shared';
import { useIndeterminateCheckbox } from '@/hooks/useIndeterminateCheckbox';
import type { AgentLlmEvalScenario } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';

// NOTE: kept as a hand-rolled ``<table>`` (not migrated to the shared
// ``CustomTable``). The cross-page persistent bulk selection, the
// tri-state select-all header (native ``indeterminate``), and the
// select-driven row highlight (``bg-primary/5``) can't be reproduced
// faithfully via ``CustomTable``'s column API without behavior risk.
export default function ScenariosTable({
  scenarios,
  isLoading,
  onEdit,
  onDelete,
  onRun,
  isRunning,
  selectedIds,
  onToggleRow,
  onToggleAll,
}: {
  scenarios: AgentLlmEvalScenario[];
  isLoading: boolean;
  onEdit: (s: AgentLlmEvalScenario) => void;
  onDelete: (s: AgentLlmEvalScenario) => void;
  // Single-scenario eval trigger. The parent owns the mutation so its
  // ``isPending`` disables every row's Run button at once — prevents a
  // second click while the first request is still in flight.
  onRun: (s: AgentLlmEvalScenario) => void;
  isRunning: boolean;
  // Bulk-selection state. ``selectedIds`` is the set of scenario ids
  // currently checked — the parent owns it so selection persists across
  // pages (a Gmail-style pattern; the header checkbox only toggles the
  // CURRENT page).
  selectedIds: Set<string>;
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
}) {
  const currentPageIds = useMemo(() => scenarios.map((s) => s.id), [scenarios]);
  const currentPageSelectedCount = useMemo(
    () => currentPageIds.filter((id) => selectedIds.has(id)).length,
    [currentPageIds, selectedIds],
  );
  // Tri-state select-all (some-but-not-all → native ``indeterminate``).
  const { ref: headerCheckboxRef, allSelected: allOnPageSelected } = useIndeterminateCheckbox(
    scenarios.length,
    currentPageSelectedCount,
  );

  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading scenarios…
      </div>
    );
  }
  if (scenarios.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        No scenarios yet. Create one, import a CSV, or use Auto-generate.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="w-10 px-3 py-2 text-left">
              <input
                ref={headerCheckboxRef}
                type="checkbox"
                aria-label="Select all on this page"
                checked={allOnPageSelected}
                onChange={onToggleAll}
                className="cursor-pointer accent-primary"
              />
            </th>
            <th className="px-3 py-2 text-left">Scenario</th>
            <th className="px-3 py-2 text-left">Prompt</th>
            {/* Fixed-width tags + source columns so the Prompt column can
                grow into the leftover space without squeezing them to a
                sliver (which caused tag chips to wrap vertically). */}
            <th className="w-[220px] px-3 py-2 text-left">Tags</th>
            <th className="w-[100px] px-3 py-2 text-left">Source</th>
            <th className="w-[110px] px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => (
            <tr
              key={s.id}
              className={cn('border-t border-border/60', selectedIds.has(s.id) && 'bg-primary/5')}
            >
              <td className="w-10 px-3 py-2 align-top">
                <input
                  type="checkbox"
                  aria-label={`Select ${s.scenario_key}`}
                  checked={selectedIds.has(s.id)}
                  onChange={() => onToggleRow(s.id)}
                  className="cursor-pointer accent-primary"
                />
              </td>
              <td className="px-3 py-2 align-top font-medium text-foreground">{s.scenario_key}</td>
              <td className="w-full px-3 py-2 align-top text-muted-foreground">
                <span
                  className="line-clamp-2 block max-w-[700px] xl:max-w-[900px]"
                  title={s.prompt}
                >
                  {s.prompt}
                </span>
              </td>
              <td className="w-[220px] px-3 py-2 align-top">
                <div className="flex flex-wrap gap-1">
                  {/* Tool-aware chip (Phase 2) — surfaces scenarios whose
                      generator pre-labeled the expected tool call so an
                      operator can see at a glance which rows will run the
                      deterministic ``tool_selection`` metric. */}
                  {s.expected_tools && s.expected_tools.length > 0 ? (
                    <span
                      title={s.expected_tools
                        .map((t) => t.name)
                        .filter(Boolean)
                        .join(', ')}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary ring-1 ring-primary/20"
                    >
                      <Wrench className="size-2.5" />
                      tool
                    </span>
                  ) : null}
                  {(s.tags ?? []).map((t) => (
                    <span
                      key={t}
                      title={t}
                      className="max-w-[200px] truncate rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 align-top">
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {s.source}
                </span>
              </td>
              <td className="px-3 py-2 align-top">
                <div className="flex items-center justify-end gap-1">
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => onRun(s)}
                    disabled={isRunning}
                    className="rounded p-1 text-muted-foreground hover:bg-primary/10 hover:text-primary disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted-foreground"
                    aria-label={`Run ${s.scenario_key}`}
                    title="Run this scenario"
                  >
                    <Play className="size-4" />
                  </CustomButton>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => onEdit(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Edit scenario"
                  >
                    <Pencil className="size-4" />
                  </CustomButton>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => onDelete(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    aria-label="Delete scenario"
                  >
                    <Trash2 className="size-4" />
                  </CustomButton>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
