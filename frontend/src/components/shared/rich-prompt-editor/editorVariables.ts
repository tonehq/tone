/**
 * Editor-side helpers for custom variables. Custom variables live entirely inside the
 * document (each chip carries its `default`), so these read/mutate the doc directly —
 * there is no separate store. Every mutation dispatches a transaction, which fires the
 * editor's `onUpdate` and keeps the serialized RHF value in sync.
 */

import type { Editor } from '@tiptap/react';

import { VARIABLE_MENTION_NAME } from './serialization';

export interface CustomVariable {
  key: string;
  default: string;
}

/** Strip characters that would corrupt a `{{key|default}}` token. */
export function sanitizeVariableKey(raw: string): string {
  return raw.replace(/[^a-zA-Z0-9_]/g, '');
}

export function sanitizeVariableDefault(raw: string): string {
  return raw.replace(/[{}\n]/g, '');
}

/** Unique custom variables currently present in the document (first default wins). */
export function getCustomVariables(editor: Editor): CustomVariable[] {
  const map = new Map<string, string>();
  editor.state.doc.descendants((node) => {
    if (node.type.name === VARIABLE_MENTION_NAME) {
      const def = node.attrs.default;
      if (def !== null && def !== undefined && !map.has(node.attrs.key)) {
        map.set(node.attrs.key, def as string);
      }
    }
    return true;
  });
  return Array.from(map, ([key, def]) => ({ key, default: def }));
}

export function insertCustomVariable(editor: Editor, key: string, def: string): void {
  editor
    .chain()
    .focus()
    .insertContent([
      { type: VARIABLE_MENTION_NAME, attrs: { key, default: def } },
      { type: 'text', text: ' ' },
    ])
    .run();
}

/** Set the default on every chip with this key. */
export function updateCustomVariableDefault(
  editor: Editor,
  key: string,
  nextDefault: string,
): void {
  const { state, view } = editor;
  const tr = state.tr;
  let changed = false;
  state.doc.descendants((node, pos) => {
    if (node.type.name === VARIABLE_MENTION_NAME && node.attrs.key === key) {
      tr.setNodeMarkup(pos, undefined, { ...node.attrs, default: nextDefault });
      changed = true;
    }
    return true;
  });
  if (changed) view.dispatch(tr);
}

/** Remove every chip with this key from the document. */
export function removeCustomVariable(editor: Editor, key: string): void {
  const { state, view } = editor;
  const positions: number[] = [];
  state.doc.descendants((node, pos) => {
    if (node.type.name === VARIABLE_MENTION_NAME && node.attrs.key === key) positions.push(pos);
    return true;
  });
  if (!positions.length) return;
  const tr = state.tr;
  // Delete from the end so earlier positions stay valid (inline atoms have size 1).
  positions.sort((a, b) => b - a).forEach((pos) => tr.delete(pos, pos + 1));
  view.dispatch(tr);
}
