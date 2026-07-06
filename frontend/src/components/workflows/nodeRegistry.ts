import { GitBranch, Globe, MessageSquare, PhoneOff, Wrench, type LucideIcon } from 'lucide-react';

import type { WorkflowNodeType } from '@/types/workflow';

export interface NodeAccent {
  /** icon-chip + accent classes */
  chip: string;
  /** 2px top accent bar */
  bar: string;
  /** hex for the minimap */
  mini: string;
}

export interface NodeTypeMeta {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: LucideIcon;
  category: 'Conversation' | 'Logic' | 'Actions';
  accent: NodeAccent;
  hasTarget: boolean;
  terminal: boolean;
  deletable: boolean;
  /** default `data` payload when a node of this type is created */
  defaultData: () => Record<string, unknown>;
}

// Concrete accents (Tailwind can't see dynamic class names, so spell them out).
const ACCENTS: Record<WorkflowNodeType, NodeAccent> = {
  conversation: {
    chip: 'bg-indigo-500/10 ring-1 ring-inset ring-indigo-500/20 text-indigo-600 dark:text-indigo-300',
    bar: 'bg-indigo-500/70',
    mini: '#6366f1',
  },
  decision: {
    chip: 'bg-amber-500/10 ring-1 ring-inset ring-amber-500/20 text-amber-600 dark:text-amber-300',
    bar: 'bg-amber-500/70',
    mini: '#f59e0b',
  },
  tool: {
    chip: 'bg-violet-500/10 ring-1 ring-inset ring-violet-500/20 text-violet-600 dark:text-violet-300',
    bar: 'bg-violet-500/70',
    mini: '#8b5cf6',
  },
  endCall: {
    chip: 'bg-rose-500/10 ring-1 ring-inset ring-rose-500/20 text-rose-600 dark:text-rose-300',
    bar: 'bg-rose-500/70',
    mini: '#f43f5e',
  },
  apiRequest: {
    chip: 'bg-teal-500/10 ring-1 ring-inset ring-teal-500/20 text-teal-600 dark:text-teal-300',
    bar: 'bg-teal-500/70',
    mini: '#14b8a6',
  },
};

export const NODE_REGISTRY: Record<WorkflowNodeType, NodeTypeMeta> = {
  conversation: {
    type: 'conversation',
    label: 'Conversation',
    description: 'Talk to the caller and extract variables',
    icon: MessageSquare,
    category: 'Conversation',
    accent: ACCENTS.conversation,
    hasTarget: true,
    terminal: false,
    deletable: true,
    defaultData: () => ({
      prompt: '',
      messagePlan: { firstMessage: '' },
      variableExtractionPlan: { output: [] },
      toolIds: [],
    }),
  },
  decision: {
    type: 'decision',
    label: 'Decision',
    description: 'Pure router — branches on its outgoing edges',
    icon: GitBranch,
    category: 'Logic',
    accent: ACCENTS.decision,
    hasTarget: true,
    terminal: false,
    deletable: true,
    defaultData: () => ({ prompt: '' }),
  },
  tool: {
    type: 'tool',
    label: 'Tool',
    description: 'Run a webhook / custom / MCP tool',
    icon: Wrench,
    category: 'Actions',
    accent: ACCENTS.tool,
    hasTarget: true,
    terminal: false,
    deletable: true,
    defaultData: () => ({ toolId: '' }),
  },
  endCall: {
    type: 'endCall',
    label: 'End Call',
    description: 'Say goodbye and hang up',
    icon: PhoneOff,
    category: 'Actions',
    accent: ACCENTS.endCall,
    hasTarget: true,
    terminal: true,
    deletable: true,
    defaultData: () => ({ messagePlan: { firstMessage: 'Thanks for calling. Goodbye!' } }),
  },
  apiRequest: {
    type: 'apiRequest',
    label: 'API Request',
    description: 'Call an HTTP API and use the response',
    icon: Globe,
    category: 'Actions',
    accent: ACCENTS.apiRequest,
    hasTarget: true,
    terminal: false,
    deletable: true,
    defaultData: () => ({
      description: 'API request tool',
      method: 'GET',
      url: '',
      headers: [],
      requestBody: [],
      staticBody: [],
      responseFields: [],
      aliases: [],
      messages: {},
    }),
  },
};

export const NODE_CATEGORIES: { heading: string; items: NodeTypeMeta[] }[] = [
  { heading: 'Conversation', items: [NODE_REGISTRY.conversation] },
  { heading: 'Logic', items: [NODE_REGISTRY.decision] },
  {
    heading: 'Actions',
    items: [NODE_REGISTRY.tool, NODE_REGISTRY.apiRequest, NODE_REGISTRY.endCall],
  },
];

export const ALL_NODE_TYPES = Object.keys(NODE_REGISTRY) as WorkflowNodeType[];
