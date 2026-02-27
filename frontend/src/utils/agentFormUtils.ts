import type { AgentFormState, ApiAgent } from '@/types/agent';

export const defaultFormState = (agentType: 'inbound' | 'outbound'): AgentFormState => ({
  name: agentType === 'inbound' ? 'My Inbound Assistant' : 'My Outbound Assistant',
  description: '',
  aiModel: null,
  end_call_message: '',
  first_message: '',
  customVocabulary: [],
  filterWords: [],
  language: 'en',
  voiceProvider: null,
  sttProvider: null,
  patienceLevel: 'low',
  speechRecognition: 'fast',
  voiceSpeed: 50,
  voiceVolume: 100,
  interruptionSensitivity: 2,
  voicePrompting: '',
  useRealisticFillerWords: false,
  callRecording: false,
  callTranscription: false,
  phoneNumbers: [],
  channels: [],
});

function parseStringArray(val: string | string[] | null | undefined): string[] {
  if (Array.isArray(val)) return val;
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return val ? [val] : [];
    }
  }
  return [];
}

function parseBoolean(val: boolean | string | null | undefined): boolean {
  if (typeof val === 'boolean') return val;
  if (val === null || val === undefined) return false;
  return String(val).toLowerCase() === 'true' || String(val) === '1';
}

export function apiAgentToFormState(
  api: ApiAgent | null,
  agentType: 'inbound' | 'outbound',
): AgentFormState {
  const defaults = defaultFormState(agentType);
  if (!api) return defaults;
  return {
    ...defaults,
    name: api.name ?? defaults.name,
    description: api.description ?? defaults.description,
    first_message: api.first_message ?? defaults.first_message,
    end_call_message: api.end_call_message ?? defaults.end_call_message,
    voicePrompting: (api.system_prompt as string) ?? defaults.voicePrompting,
    customVocabulary: parseStringArray(api.custom_vocabulary),
    filterWords: parseStringArray(api.filter_words),
    useRealisticFillerWords: parseBoolean(api.realistic_filler_words),
    language: (api.language as string) ?? defaults.language,
    voiceSpeed:
      typeof api.voice_speed === 'number'
        ? api.voice_speed
        : Number(api.voice_speed) || defaults.voiceSpeed,
    patienceLevel: (api.patience_level as string) ?? defaults.patienceLevel,
    speechRecognition: (api.speech_recognition as string) ?? defaults.speechRecognition,
    callRecording: parseBoolean(api.call_recording),
    callTranscription: parseBoolean(api.call_transcription),
    aiModel: api.llm_service_id ?? defaults.aiModel,
    voiceProvider: api.tts_service_id ?? defaults.voiceProvider,
    sttProvider: api.stt_service_id ?? defaults.sttProvider,
    phoneNumbers: api.phone_number ?? [],
    channels: api.channels ?? [],
  };
}

export function formStateToUpsertPayload(
  form: AgentFormState,
  agentType: 'inbound' | 'outbound',
  existingId?: number,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    name: form.name,
    description: form.description || null,
    agent_type: agentType,
    first_message: form.first_message || null,
    end_call_message: form.end_call_message || null,
    system_prompt: form.voicePrompting || null,
    custom_vocabulary: form.customVocabulary.length ? JSON.stringify(form.customVocabulary) : null,
    filter_words: form.filterWords.length ? JSON.stringify(form.filterWords) : null,
    realistic_filler_words: form.useRealisticFillerWords,
    language: form.language || null,
    voice_speed: form.voiceSpeed,
    patience_level: form.patienceLevel || null,
    speech_recognition: form.speechRecognition || null,
    call_recording: form.callRecording,
    call_transcription: form.callTranscription,
    llm_service_id: form.aiModel,
    tts_service_id: form.voiceProvider,
    stt_service_id: form.sttProvider,
    channel: {
      type: 'TWILIO',
    },
  };
  if (existingId != null) payload.id = existingId;
  return payload;
}
