export interface AgentGeneralFormData {
  name: string;
  description: string;
  aiModel: string;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  useRealisticFillerWords: boolean;
}

export interface AgentVoiceFormData {
  language: string;
  voiceSpeed: number;
  voiceProvider: string;
  sttProvider: string;
  patienceLevel: 'low' | 'medium' | 'high';
  speechRecognition: 'fast' | 'accurate';
}

export interface AgentCallConfigFormData {
  callRecording: boolean;
  callTranscription: boolean;
}
