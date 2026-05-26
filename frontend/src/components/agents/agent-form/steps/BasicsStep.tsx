'use client';

import { MessageCircle, Power, User2 } from 'lucide-react';
import { Controller, useFormContext } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { TextAreaField, TextInput } from '@/components/shared';
import { Switch } from '@/components/ui/switch';
import type { AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';

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
