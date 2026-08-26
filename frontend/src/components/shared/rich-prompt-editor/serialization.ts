/**
 * Round-trip between the TipTap document (ProseMirror JSON) and the plain-text
 * prompt string stored in `config.system_prompt_template`.
 *
 * Two kinds of chip:
 * - System variables → `{{key}}`. Rerevived when the key is a known system variable.
 * - Custom variables → `{{key|default}}`. The user-set default value is encoded inline
 *   (no separate storage); the pipe is what marks a token as a custom variable.
 *
 * On load, unknown `{{...}}` WITHOUT a pipe stay as literal text (never lost).
 * Paragraphs map 1:1 to newlines, so blank lines and structure survive a round trip.
 *
 * Pure functions — no TipTap runtime imports — so they can be unit-tested and reused
 * for the character count and the manage-variables panel.
 */

import { isKnownPromptVariable } from '@/constants/promptVariables';

export const VARIABLE_MENTION_NAME = 'variableMention';

/** Minimal ProseMirror JSON node shape we care about. */
export interface PMNode {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: PMNode[];
}

// Key: an identifier optionally followed by dotted identifier segments, so
// `profile.customer_name` matches but incidental prose like `{{1.0|draft}}`
// does NOT (segments must start with a letter/underscore). Then an optional
// `|default` (default may contain anything except `}`). MUST stay in sync
// with the backend regex in `core/services/pipeline/prompt_variables.py`.
const TOKEN_RE =
  /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*(?:\|([^}]*))?\}\}/g;

/** Serialize a single variable chip's attrs to its `{{...}}` token form. */
export function variableToken(key: string, def: string | null | undefined): string {
  return def !== null && def !== undefined ? `{{${key}|${def}}}` : `{{${key}}}`;
}

function serializeInline(node: PMNode): string {
  if (node.type === 'text') return node.text ?? '';
  if (node.type === VARIABLE_MENTION_NAME) {
    const key = String(node.attrs?.key ?? '');
    const def = node.attrs?.default as string | null | undefined;
    return variableToken(key, def);
  }
  if (node.type === 'hardBreak') return '\n';
  return '';
}

function serializeBlock(node: PMNode): string {
  // Paragraphs (and any unknown block with inline content) flatten to their text.
  return (node.content ?? []).map(serializeInline).join('');
}

/** Serialize a TipTap doc JSON to the plain-text prompt with `{{key}}` placeholders. */
export function serializeToText(doc: PMNode | null | undefined): string {
  if (!doc?.content?.length) return '';
  return doc.content.map(serializeBlock).join('\n');
}

function textNode(text: string): PMNode | null {
  return text ? { type: 'text', text } : null;
}

function lineToParagraph(line: string): PMNode {
  const inline: PMNode[] = [];
  let last = 0;

  // matchAll needs a fresh lastIndex each call; the literal regex is global, so
  // iterate via matchAll which manages its own cursor.
  for (const match of line.matchAll(TOKEN_RE)) {
    const key = match[1];
    const rawDefault = match[2]; // undefined when there is no `|default`
    const idx = match.index ?? 0;
    const before = textNode(line.slice(last, idx));
    if (before) inline.push(before);
    if (rawDefault !== undefined) {
      // Has a pipe → custom variable carrying its default value.
      inline.push({ type: VARIABLE_MENTION_NAME, attrs: { key, default: rawDefault } });
    } else if (isKnownPromptVariable(key)) {
      // Known system variable (no default).
      inline.push({ type: VARIABLE_MENTION_NAME, attrs: { key, default: null } });
    } else {
      // Unknown placeholder, no pipe — keep it verbatim so it round-trips untouched.
      inline.push({ type: 'text', text: match[0] });
    }
    last = idx + match[0].length;
  }

  const tail = textNode(line.slice(last));
  if (tail) inline.push(tail);

  return inline.length ? { type: 'paragraph', content: inline } : { type: 'paragraph' };
}

/** Parse a stored prompt string into TipTap doc JSON, reviving known `{{key}}` chips. */
export function parseTextToDoc(text: string | null | undefined): PMNode {
  const lines = (text ?? '').split('\n');
  const content = lines.map(lineToParagraph);
  return { type: 'doc', content: content.length ? content : [{ type: 'paragraph' }] };
}
