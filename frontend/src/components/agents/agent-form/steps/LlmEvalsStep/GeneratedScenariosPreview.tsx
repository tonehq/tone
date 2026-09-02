import { useIndeterminateCheckbox } from '@/hooks/useIndeterminateCheckbox';
import type { GeneratedScenario } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';

// Preview table for the Auto-generate flow. Kept local to this feature
// because it's a one-off shape — nothing else renders ``GeneratedScenario``.
//
// NOTE: kept as a hand-rolled ``<table>`` (not migrated to the shared
// ``CustomTable``). The sticky scroll header, the whole-row click-to-toggle,
// the checkbox ``stopPropagation`` seam, the tri-state select-all
// (native ``indeterminate``), and the unchecked-row opacity dim can't be
// reproduced faithfully via ``CustomTable`` without behavior risk.
export default function GeneratedScenariosPreview({
  rows,
  selectedKeys,
  onToggleRow,
  onToggleAll,
}: {
  rows: GeneratedScenario[];
  selectedKeys: Set<string>;
  onToggleRow: (key: string) => void;
  onToggleAll: () => void;
}) {
  // Tri-state select-all (some-but-not-all → native ``indeterminate``).
  const { ref: selectAllRef, allSelected } = useIndeterminateCheckbox(
    rows.length,
    selectedKeys.size,
  );
  return (
    <div className="flex max-h-[60vh] flex-col overflow-hidden rounded-md border border-border/60">
      <div className="overflow-y-auto">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col className="w-10" />
            <col className="w-[220px]" />
            <col />
            <col className="w-[200px]" />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-muted text-[11px] uppercase tracking-wide text-muted-foreground shadow-[0_1px_0_0_var(--border)]">
            <tr>
              <th className="px-3 py-2 text-left">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  aria-label="Select all"
                  checked={allSelected}
                  onChange={onToggleAll}
                  className="cursor-pointer accent-primary"
                />
              </th>
              <th className="px-3 py-2 text-left">Scenario</th>
              <th className="px-3 py-2 text-left">Prompt</th>
              <th className="px-3 py-2 text-left">Tags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const checked = selectedKeys.has(r.scenario_key);
              return (
                <tr
                  key={r.scenario_key}
                  className={cn(
                    'cursor-pointer border-t border-border/60 hover:bg-muted/30',
                    !checked && 'opacity-70',
                  )}
                  onClick={() => onToggleRow(r.scenario_key)}
                >
                  <td className="px-3 py-2 align-top">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleRow(r.scenario_key)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select ${r.scenario_key}`}
                      className="cursor-pointer accent-primary"
                    />
                  </td>
                  <td className="px-3 py-2 align-top font-medium text-foreground break-words">
                    {r.scenario_key}
                  </td>
                  <td className="px-3 py-2 align-top text-muted-foreground">
                    <span className="line-clamp-3 block break-words" title={r.prompt}>
                      {r.prompt}
                    </span>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      {r.tags.map((t) => (
                        <span
                          key={t}
                          className="max-w-[160px] truncate rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
