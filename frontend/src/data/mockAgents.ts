import { Agent } from '@/types/agent';

export const mockAgents: Agent[] = [
  {
    id: '1',
    name: 'My Outbound Assistant',
    type: 'outbound',
    status: 'active',
    phoneNumber: undefined,
    createdAt: '2026-01-30T12:59:00Z',
    lastEdited: '2026-01-30T12:59:00Z',
    avatar: undefined,
  },
  {
    id: '2',
    name: 'My Outbound Assistant',
    type: 'outbound',
    status: 'active',
    phoneNumber: undefined,
    createdAt: '2026-01-30T12:59:00Z',
    lastEdited: '2026-01-30T12:59:00Z',
    avatar: undefined,
  },
  {
    id: '3',
    name: 'My Inbound Assistant',
    type: 'inbound',
    status: 'active',
    phoneNumber: undefined,
    createdAt: '2026-01-29T14:25:00Z',
    lastEdited: '2026-01-29T14:25:00Z',
    avatar: '/avatars/assistant.jpg',
  },
  {
    id: '4',
    name: 'karthik',
    type: 'outbound',
    status: 'active',
    phoneNumber: undefined,
    createdAt: '2026-01-29T13:24:00Z',
    lastEdited: '2026-01-29T13:24:00Z',
    avatar: '/avatars/karthik.jpg',
  },
  {
    id: '5',
    name: 'My Inbound Assistant',
    type: 'inbound',
    status: 'active',
    phoneNumber: '+1 740 520 4895',
    createdAt: '2026-01-27T11:46:00Z',
    lastEdited: '2026-01-27T11:46:00Z',
    avatar: undefined,
  },
  {
    id: '6',
    name: 'My Outbound Assistant',
    type: 'outbound',
    status: 'draft',
    phoneNumber: undefined,
    createdAt: '2025-09-01T13:51:00Z',
    lastEdited: '2025-09-01T13:51:00Z',
    avatar: undefined,
  },
];

export const aiModels = [
  { value: 'gpt-4.1', label: 'GPT-4.1', provider: 'OpenAI' },
  { value: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', provider: 'OpenAI' },
  { value: 'claude-3-opus', label: 'Claude 3 Opus', provider: 'Anthropic' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet', provider: 'Anthropic' },
];

export const timezones = [
  { value: 'Europe/Berlin', label: 'Europe/Berlin' },
  { value: 'America/New_York', label: 'America/New York' },
  { value: 'America/Los_Angeles', label: 'America/Los Angeles' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo' },
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata' },
  { value: 'UTC', label: 'UTC' },
];

export const languages = [
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'es', label: 'Spanish', flag: '🇪🇸' },
  { value: 'fr', label: 'French', flag: '🇫🇷' },
  { value: 'de', label: 'German', flag: '🇩🇪' },
  { value: 'it', label: 'Italian', flag: '🇮🇹' },
  { value: 'pt', label: 'Portuguese', flag: '🇵🇹' },
];

export const voiceProviders = [
  { value: 'elevenlabs', label: 'ElevenLabs' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure', label: 'Azure' },
];

export const sttProviders = [
  { value: 'deepgram', label: 'Deepgram' },
  { value: 'openai-whisper', label: 'OpenAI Whisper' },
  { value: 'azure', label: 'Azure' },
];

export const voices = [
  { value: 'jessica', label: 'Jessica', provider: 'ElevenLabs', accent: 'american', gender: 'female' },
  { value: 'michael', label: 'Michael', provider: 'ElevenLabs', accent: 'american', gender: 'male' },
  { value: 'emma', label: 'Emma', provider: 'ElevenLabs', accent: 'british', gender: 'female' },
  { value: 'james', label: 'James', provider: 'ElevenLabs', accent: 'british', gender: 'male' },
];
