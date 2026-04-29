import { BrainCircuit, Layers, Mic, Server, Volume2 } from 'lucide-react';
import { createElement } from 'react';

// ── Pagination ─────────────────────────────────────────────────────

export const PROVIDERS_PAGE_SIZE = 15;
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
