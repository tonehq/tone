'use client';

import { Switch } from '@/components/ui/switch';
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
    <div className="space-y-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Call Recording</h3>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Enable recording of all calls for review.
          </p>
        </div>
        <Switch
          checked={formData.callRecording}
          onCheckedChange={(checked) => onFormChange({ callRecording: checked })}
        />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Call Transcription</h3>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Automatically transcribe all calls to text.
          </p>
        </div>
        <Switch
          checked={formData.callTranscription}
          onCheckedChange={(checked) => onFormChange({ callTranscription: checked })}
        />
      </div>
    </div>
  );
}
