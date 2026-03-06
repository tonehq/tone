'use client';

import { Switch } from '@/components/ui/switch';
import { Phone } from 'lucide-react';
import type { AgentCallConfigFormData } from './types';

interface CallConfigurationTabProps {
  formData: AgentCallConfigFormData;
  onFormChange: (partial: Partial<AgentCallConfigFormData>) => void;
}

export default function CallConfigurationTab({
  formData,
  onFormChange,
}: CallConfigurationTabProps) {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border bg-background shadow-sm">
        <div className="flex items-center gap-3 border-b border-border/60 px-5 py-3.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Phone size={16} className="text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Call Settings</h2>
            <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
              Configure recording and transcription for calls.
            </p>
          </div>
        </div>
        <div className="px-5 py-4">
          <div className="flex items-center justify-between border-b border-border/40 py-4">
            <div>
              <h3 className="text-[13px] font-medium text-foreground">Call Recording</h3>
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                Enable recording of all calls for review.
              </p>
            </div>
            <Switch
              checked={formData.callRecording}
              onCheckedChange={(checked) => onFormChange({ callRecording: checked })}
            />
          </div>

          <div className="flex items-center justify-between py-4">
            <div>
              <h3 className="text-[13px] font-medium text-foreground">Call Transcription</h3>
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                Automatically transcribe all calls to text.
              </p>
            </div>
            <Switch
              checked={formData.callTranscription}
              onCheckedChange={(checked) => onFormChange({ callTranscription: checked })}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
