export interface AgentGeneralFormData {
  name: string;
  description: string;
  aiModel: number | null;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  useRealisticFillerWords: boolean;
}

export interface AgentVoiceFormData {
  language: string;
  voiceSpeed: number;
  voiceProvider: number | null;
  sttProvider: number | null;
  patienceLevel: 'low' | 'medium' | 'high';
  speechRecognition: 'fast' | 'accurate';
}

export interface AgentCallConfigFormData {
  callRecording: boolean;
  callTranscription: boolean;
}
