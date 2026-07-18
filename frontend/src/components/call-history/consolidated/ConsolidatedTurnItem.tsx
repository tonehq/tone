'use client';

import { durationToneClass } from '@/components/call-history/tools-mcp/helpers';
import type { ConsolidatedTurn } from '@/types/callLog';
import { cn } from '@/utils/cn';
import React from 'react';

import ConsolidatedToolCallRow from './ConsolidatedToolCallRow';
import { formatTurnLatency, turnLatencyTone } from './helpers';

interface ConsolidatedTurnProps {
  turn: ConsolidatedTurn;
  /** When true, emit a small "Turn N" divider above this turn — used by the
   *  parent list to break up the chat visually without wrapping each turn in
   *  a card. Defaults to true; the first turn can suppress it. */
  showDivider?: boolean;
}

/**
 * One conversational turn rendered as a WhatsApp-style flat chat sequence:
 * user bubble on the left, tool invocations centered inline, a latency chip
 * between the two speakers, then the assistant reply on the right. No card
 * wrapper — turns are separated only by a subtle centered "Turn N" divider so
 * the whole tab reads as a continuous conversation.
 *
 * Empty user/assistant speeches are skipped entirely rather than showing a
 * placeholder bubble — a bot-opened turn shouldn't leave a ghost "no user
 * speech" bubble hanging in the timeline.
 */
const ConsolidatedTurnItem: React.FC<ConsolidatedTurnProps> = ({ turn, showDivider = true }) => {
  const tools = turn.tool_calls;
  const latencyTone = turnLatencyTone(turn.user_bot_latency_ms);
  const latencyText = formatTurnLatency(turn.user_bot_latency_ms);
  const hasUser = !!turn.user_speech && turn.user_speech.trim().length > 0;
  const hasBot = !!turn.bot_speech && turn.bot_speech.trim().length > 0;
  const hasLatency = turn.user_bot_latency_ms != null;

  return (
    <div className="flex flex-col gap-3">
      {showDivider && <TurnDivider turnNumber={turn.turn_number} />}

      {hasUser && <ChatBubble role="user" text={turn.user_speech!} />}

      {tools.length > 0 && (
        <div className="mx-auto flex w-full max-w-[60%] flex-col gap-2">
          {tools.map((tool) => (
            <ConsolidatedToolCallRow key={tool.id} tool={tool} />
          ))}
        </div>
      )}

      {hasLatency && (
        <div className="flex justify-center">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full border border-border/60 bg-background px-2 py-0.5 text-[10.5px] font-medium tabular-nums',
              durationToneClass(latencyTone),
            )}
          >
            <span
              aria-hidden
              className={cn(
                'size-1.5 rounded-full',
                latencyTone === 'good' && 'bg-emerald-500',
                latencyTone === 'warn' && 'bg-amber-500',
                latencyTone === 'bad' && 'bg-rose-500',
                latencyTone === 'neutral' && 'bg-muted-foreground/40',
              )}
            />
            {latencyText}
          </span>
        </div>
      )}

      {hasBot && <ChatBubble role="assistant" text={turn.bot_speech!} />}
    </div>
  );
};

/** Centered subtle divider between turns — mimics WhatsApp's date separator. */
function TurnDivider({ turnNumber }: { turnNumber: number }) {
  return (
    <div className="flex items-center justify-center gap-2 py-1">
      <span className="h-px flex-1 bg-border/50" />
      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Turn {turnNumber}
      </span>
      <span className="h-px flex-1 bg-border/50" />
    </div>
  );
}

interface ChatBubbleProps {
  role: 'user' | 'assistant';
  text: string;
}

/**
 * One chat bubble. User bubbles hug the left with a muted background;
 * assistant bubbles hug the right with a tinted (primary) background — same
 * side convention as the Transcription tab, so switching between the two tabs
 * keeps roles in the same visual position.
 */
function ChatBubble({ role, text }: ChatBubbleProps) {
  const isUser = role === 'user';
  return (
    <div className={cn('flex', isUser ? 'justify-start' : 'justify-end')}>
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm',
          isUser
            ? 'rounded-bl-sm bg-muted text-foreground'
            : 'rounded-br-sm bg-primary/10 text-foreground dark:bg-primary/20',
        )}
      >
        <p className="mb-0.5 text-xs font-medium opacity-70">{isUser ? 'User' : 'Assistant'}</p>
        <p className="whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}

export default ConsolidatedTurnItem;
