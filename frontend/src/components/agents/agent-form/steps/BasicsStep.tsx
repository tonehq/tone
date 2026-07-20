'use client';

import { MessageCircle, PhoneCall, Power, User2 } from 'lucide-react';
import { Controller, useFormContext } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CheckboxField, TextAreaField, TextInput } from '@/components/shared';
import { Switch } from '@/components/ui/switch';
import type { AgentDirection, AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';

/** Two booleans → the persisted agent_type. Returns null when neither is set, so the
 *  caller can block clearing both (at least one call mode is required). */
function deriveAgentType(inbound: boolean, outbound: boolean): AgentDirection | null {
  if (inbound && outbound) return 'both';
  if (inbound) return 'inbound';
  if (outbound) return 'outbound';
  return null;
}

export default function BasicsStep() {
  const { control } = useFormContext<AgentFormState>();

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        icon={<User2 className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.indigo}
        title="Identity"
        description="How this agent appears in the workspace."
      >
        <TextInput
          name="name"
          label="Agent name"
          control={control}
          rules={{ required: 'Name is required', maxLength: { value: 120, message: 'Too long' } }}
          placeholder="e.g. Acme Sales Concierge"
          isRequired
        />
        <TextAreaField
          id="description"
          name="description"
          label="Description"
          control={control}
          rows={3}
          placeholder="What is this agent for? Who will it talk to?"
        />
      </SectionCard>

      <SectionCard
        icon={<MessageCircle className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.amber}
        title="Conversation messages"
        description="What the agent says at the start and the end of a call."
      >
        <TextAreaField
          id="first_message"
          name="config.first_message"
          label="First message"
          control={control}
          rows={2}
          placeholder="e.g. Hi there, you've reached Acme. How can I help today?"
          helperText="Spoken by the agent the moment the call connects."
        />
        <TextAreaField
          id="end_call_message"
          name="config.end_call_message"
          label="End call message"
          control={control}
          rows={2}
          placeholder="e.g. Thanks for calling Acme. Have a great day!"
          helperText="Message sent at the end of a conversation."
        />
      </SectionCard>

      <Controller
        name="agent_type"
        control={control}
        render={({ field }) => {
          const value = (field.value as AgentDirection) ?? 'inbound';
          const inbound = value === 'inbound' || value === 'both';
          const outbound = value === 'outbound' || value === 'both';
          return (
            <SectionCard
              icon={<PhoneCall className="size-3.5" strokeWidth={2.25} />}
              iconClassName={ACCENTS.indigo}
              title="Call mode"
              description="Which call directions this agent handles. Outbound (or Both) unlocks scheduling calls to contacts."
            >
              <div className="flex flex-col gap-3">
                <CheckboxField
                  id="agent-mode-inbound"
                  label="Inbound — answers incoming calls"
                  checked={inbound}
                  onCheckedChange={(v) => {
                    const next = deriveAgentType(!!v, outbound);
                    if (next) field.onChange(next);
                  }}
                />
                <CheckboxField
                  id="agent-mode-outbound"
                  label="Outbound — places calls to contacts"
                  checked={outbound}
                  onCheckedChange={(v) => {
                    const next = deriveAgentType(inbound, !!v);
                    if (next) field.onChange(next);
                  }}
                />
                <p className="text-xs text-muted-foreground">At least one call mode is required.</p>
              </div>
            </SectionCard>
          );
        }}
      />

      <Controller
        name="is_active"
        control={control}
        render={({ field }) => (
          <SectionCard
            icon={<Power className="size-3.5" strokeWidth={2.25} />}
            iconClassName={cn(field.value ? ACCENTS.emerald : ACCENTS.muted)}
            title={field.value ? 'Accepting traffic' : 'Paused'}
            description={
              field.value
                ? 'Calls are routed to this agent.'
                : 'Save with this off to keep the agent dark.'
            }
            action={
              <Switch
                checked={!!field.value}
                onCheckedChange={(v) => field.onChange(!!v)}
                aria-label="Active — accept traffic"
              />
            }
          />
        )}
      />
    </div>
  );
}
