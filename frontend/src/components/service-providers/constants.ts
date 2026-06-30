import { BrainCircuit, Layers, Mic, Server, Volume2 } from 'lucide-react';
import { createElement } from 'react';

// ── Pagination ─────────────────────────────────────────────────────

export const PROVIDERS_PAGE_SIZE = 15;
export const SERVICES_PAGE_SIZE = 15;
export const MODELS_PAGE_SIZE = 10;

export const PROVIDER_TYPE_TABS = [
  { key: 'all', label: 'All', icon: createElement(Layers, { className: 'size-3.5' }) },
  { key: 'llm', label: 'LLM', icon: createElement(BrainCircuit, { className: 'size-3.5' }) },
  { key: 'stt', label: 'STT', icon: createElement(Mic, { className: 'size-3.5' }) },
  { key: 'tts', label: 'TTS', icon: createElement(Volume2, { className: 'size-3.5' }) },
];

// ── Style maps ─────────────────────────────────────────────────────

export const TYPE_BADGE_STYLES: Record<string, string> = {
  llm: 'bg-violet-500/10 text-violet-600 dark:bg-violet-500/20 dark:text-violet-400 hover:bg-violet-500/10',
  stt: 'bg-sky-500/10 text-sky-600 dark:bg-sky-500/20 dark:text-sky-400 hover:bg-sky-500/10',
  tts: 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 hover:bg-amber-500/10',
  telephony:
    'bg-teal-500/10 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400 hover:bg-teal-500/10',
};

export const TYPE_ICON_STYLES: Record<string, string> = {
  llm: 'bg-violet-500/10 text-violet-600 dark:bg-violet-500/20 dark:text-violet-400',
  stt: 'bg-sky-500/10 text-sky-600 dark:bg-sky-500/20 dark:text-sky-400',
  tts: 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400',
  telephony: 'bg-teal-500/10 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400',
};

export const TYPE_ICONS: Record<string, React.ReactNode> = {
  llm: createElement(BrainCircuit, { className: 'size-4' }),
  stt: createElement(Mic, { className: 'size-4' }),
  tts: createElement(Volume2, { className: 'size-4' }),
  telephony: createElement(Server, { className: 'size-4' }),
};

export const STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-500',
  inactive: 'bg-zinc-400 dark:bg-zinc-500',
};

// ── Provider Logos ─────────────────────────────────────────────────
// Maps a provider's internal name (lowercase, stripped of separators)
// to a remote favicon/logo URL. Used by ServiceCard to render the real
// brand mark instead of a generic icon.

const FAVICON = (domain: string) => `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;

// Local assets bundled in /frontend/public — used for brand marks that
// Google's favicon service doesn't return cleanly (subdomain products,
// niche providers, etc.). Files live in /public/provider-logos/.
const LOCAL = (filename: string) => `/provider-logos/${filename}`;

export const PROVIDER_LOGOS: Record<string, string> = {
  // ── LLM ──
  openai: FAVICON('openai.com'),
  anthropic: FAVICON('anthropic.com'),
  groq: FAVICON('groq.com'),
  google: FAVICON('google.com'),
  gemini: LOCAL('gemini.png'),
  vertexai: FAVICON('cloud.google.com'),
  mistral: FAVICON('mistral.ai'),
  cohere: FAVICON('cohere.com'),
  together: FAVICON('together.ai'),
  fireworks: FAVICON('fireworks.ai'),
  xai: FAVICON('x.ai'),
  grok: FAVICON('x.ai'),
  perplexity: FAVICON('perplexity.ai'),
  ollama: FAVICON('ollama.com'),
  deepseek: FAVICON('deepseek.com'),
  azure: FAVICON('azure.com'),
  azureopenai: FAVICON('azure.com'),
  aws: FAVICON('aws.amazon.com'),
  bedrock: FAVICON('aws.amazon.com'),
  amazon: FAVICON('amazon.com'),

  // ── STT ──
  deepgram: FAVICON('deepgram.com'),
  assemblyai: FAVICON('assemblyai.com'),
  whisper: FAVICON('openai.com'),
  speechmatics: FAVICON('speechmatics.com'),
  rev: FAVICON('rev.com'),
  gladia: FAVICON('gladia.io'),

  // ── TTS ──
  elevenlabs: FAVICON('elevenlabs.io'),
  cartesia: FAVICON('cartesia.ai'),
  sonic: LOCAL('sonic.png'),
  cartesiasonic: LOCAL('sonic.png'),
  playht: FAVICON('play.ht'),
  rime: FAVICON('rime.ai'),
  resemble: FAVICON('resemble.ai'),
  inworld: FAVICON('inworld.ai'),
  lmnt: FAVICON('lmnt.com'),
  smallest: FAVICON('smallest.ai'),

  // ── OAuth / App integrations ──
  googlecalendar: FAVICON('calendar.google.com'),
  googlesheets: FAVICON('sheets.google.com'),
  googledrive: FAVICON('drive.google.com'),
  gmail: FAVICON('mail.google.com'),
  hubspot: FAVICON('hubspot.com'),
  notion: FAVICON('notion.so'),
  slack: FAVICON('slack.com'),
  github: FAVICON('github.com'),
  linear: FAVICON('linear.app'),
  jira: FAVICON('atlassian.com'),
  salesforce: FAVICON('salesforce.com'),
  zoom: FAVICON('zoom.us'),
};

export function getProviderLogoUrl(providerName?: string | null): string | null {
  if (!providerName) return null;
  const key = providerName.toLowerCase().replace(/[-_\s./]/g, '');

  // Direct hit
  if (PROVIDER_LOGOS[key]) return PROVIDER_LOGOS[key];

  // Fallback: strip a trailing "ai" suffix so things like "gemini-ai",
  // "fireworks-ai", "perplexity-ai" still resolve when only the base
  // form is registered above. Length > 3 guard avoids stripping
  // standalone "ai".
  if (key.endsWith('ai') && key.length > 3) {
    const stripped = key.slice(0, -2);
    if (PROVIDER_LOGOS[stripped]) return PROVIDER_LOGOS[stripped];
  }

  return null;
}

// ── Service-type sections ──────────────────────────────────────────

export interface ServiceTypeSection {
  key: 'llm' | 'stt' | 'tts';
  title: string;
  description: string;
}

export const SERVICE_TYPE_SECTIONS: ServiceTypeSection[] = [
  {
    key: 'llm',
    title: 'LLM',
    description: 'Large Language Models for reasoning and generation',
  },
  {
    key: 'stt',
    title: 'STT',
    description: 'Speech-to-Text providers for transcription',
  },
  {
    key: 'tts',
    title: 'TTS',
    description: 'Text-to-Speech providers for voice synthesis',
  },
];
