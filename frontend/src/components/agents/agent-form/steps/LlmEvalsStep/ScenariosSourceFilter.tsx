import { SelectInput } from '@/components/shared';
import type { AgentLlmEvalScenarioSource } from '@/types/agentLlmEval';

import { SCENARIO_SOURCE_OPTIONS, SOURCE_FILTER_ALL_VALUE } from './constants';

/** Compact source-filter dropdown — rendered inline next to the
 * SearchBar in the folder-drill-in view so filter + search live on the
 * SAME visual row. Kept as its own component so the parent can compose
 * the row layout without inlining Radix-Select glue. */
export default function ScenariosSourceFilter({
  selectedSource,
  onSourceChange,
}: {
  selectedSource: AgentLlmEvalScenarioSource | null;
  onSourceChange: (next: AgentLlmEvalScenarioSource | null) => void;
}) {
  return (
    <div className="w-[180px] shrink-0">
      <SelectInput
        name="scenario_source"
        value={selectedSource ?? SOURCE_FILTER_ALL_VALUE}
        onValueChange={(v) =>
          onSourceChange(
            v === SOURCE_FILTER_ALL_VALUE || v == null ? null : (v as AgentLlmEvalScenarioSource),
          )
        }
        options={[
          { value: SOURCE_FILTER_ALL_VALUE, label: 'All sources' },
          ...SCENARIO_SOURCE_OPTIONS,
        ]}
      />
    </div>
  );
}
