import React from 'react';

import SelectInput from '@/components/shared/SelectInput';
import TextAreaField from '@/components/shared/TextAreaField';
import Card from './Card';
import { CONDITION_TYPE_OPTIONS } from './nodeConfigConstants';
import type { ConditionEdgeData, EdgeConditionType, WorkflowEdge } from '@/types/workflow';

interface EdgeConfigFormProps {
  edge: WorkflowEdge;
  onChangeEdge: (id: string, data: ConditionEdgeData) => void;
}

const EdgeConfigForm: React.FC<EdgeConfigFormProps> = ({ edge, onChangeEdge }) => {
  const cond = (edge.data as ConditionEdgeData | undefined)?.condition ?? {
    type: 'ai',
    prompt: '',
  };
  const set = (type: EdgeConditionType, prompt: string) =>
    onChangeEdge(edge.id, { condition: { type, prompt } });
  const isLogic = cond.type === 'logic';

  return (
    <div className="flex flex-col gap-5">
      <Card className="bg-card">
        <div className="font-mono text-xs text-muted-foreground">
          {edge.source} <span className="text-primary">→</span> {edge.target}
        </div>
      </Card>

      <SelectInput
        name="condition-type"
        label="Condition type"
        options={CONDITION_TYPE_OPTIONS}
        value={cond.type}
        onValueChange={(v) => set(v as EdgeConditionType, cond.prompt)}
      />

      <TextAreaField
        name="condition-prompt"
        label={isLogic ? 'Liquid expression' : 'Condition'}
        rows={4}
        value={cond.prompt}
        onChange={(e) => set(cond.type, e.target.value)}
        placeholder={
          isLogic ? '{{ user_confirmed == true }}' : 'e.g. user said yes (leave blank for always)'
        }
        helperText={
          isLogic
            ? 'Evaluated against extracted variables. No LLM call.'
            : 'The agent decides if this is satisfied. Leave blank to always follow this edge.'
        }
        className={isLogic ? 'font-mono' : undefined}
      />
    </div>
  );
};

export default EdgeConfigForm;
