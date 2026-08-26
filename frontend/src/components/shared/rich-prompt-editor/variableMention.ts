'use client';

import { computePosition, flip, offset, shift } from '@floating-ui/dom';
import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer, ReactRenderer } from '@tiptap/react';
import Suggestion, { type SuggestionOptions, type SuggestionProps } from '@tiptap/suggestion';

import { PROMPT_VARIABLES, type PromptVariable } from '@/constants/promptVariables';

import SuggestionList, { type SuggestionListRef } from './SuggestionList';
import { VARIABLE_MENTION_NAME, variableToken } from './serialization';
import VariableChip from './VariableChip';

/** Live source of extra (per-agent Profile) variables to include in the picker.
 * The default returns `[]`; the editor field swaps in a ref-backed getter via
 * `createVariableMention` so the extension stays stable but the picker sees
 * fresh profile vars whenever the surrounding component re-renders. */
export type ProfileVariablesGetter = () => PromptVariable[];

function buildFilter(getProfileVars: ProfileVariablesGetter) {
  return function filterVariables(query: string): PromptVariable[] {
    const merged = [...PROMPT_VARIABLES, ...getProfileVars()];
    const q = query.trim().toLowerCase();
    if (!q) return merged;
    return merged.filter(
      (v) => v.key.toLowerCase().includes(q) || v.label.toLowerCase().includes(q),
    );
  };
}

function buildSuggestion(
  getProfileVars: ProfileVariablesGetter,
): Omit<SuggestionOptions<PromptVariable, PromptVariable>, 'editor'> {
  const filterVariables = buildFilter(getProfileVars);
  return {
    // Multi-char trigger: typing `{{` opens the variable menu. `allowedPrefixes: null`
    // lets it trigger after any character (not only after whitespace).
    char: '{{',
    allowSpaces: false,
    allowedPrefixes: null,
    items: ({ query }) => filterVariables(query),
    command: ({ editor, range, props }) => {
      editor
        .chain()
        .focus()
        .insertContentAt(range, [
          { type: VARIABLE_MENTION_NAME, attrs: { key: props.key } },
          { type: 'text', text: ' ' },
        ])
        .run();
    },
    render: () => {
      let component: ReactRenderer<SuggestionListRef> | null = null;
      let dropdown: HTMLDivElement | null = null;

      const reposition = (clientRect?: (() => DOMRect | null) | null) => {
        if (!dropdown || !clientRect) return;
        const rect = clientRect();
        if (!rect) return;
        const virtual = { getBoundingClientRect: () => rect };
        computePosition(virtual, dropdown, {
          placement: 'bottom-start',
          middleware: [offset(6), flip(), shift({ padding: 8 })],
        }).then(({ x, y }) => {
          if (dropdown) Object.assign(dropdown.style, { left: `${x}px`, top: `${y}px` });
        });
      };

      return {
        onStart: (props: SuggestionProps<PromptVariable, PromptVariable>) => {
          component = new ReactRenderer(SuggestionList, {
            props,
            editor: props.editor,
          });
          dropdown = document.createElement('div');
          dropdown.style.position = 'absolute';
          dropdown.style.top = '0';
          dropdown.style.left = '0';
          dropdown.style.zIndex = '50';
          dropdown.appendChild(component.element);
          document.body.appendChild(dropdown);
          reposition(props.clientRect);
        },
        onUpdate: (props: SuggestionProps<PromptVariable, PromptVariable>) => {
          component?.updateProps(props);
          reposition(props.clientRect);
        },
        onKeyDown: ({ event }) => {
          if (event.key === 'Escape') {
            if (dropdown) dropdown.style.display = 'none';
            return true;
          }
          if (dropdown) dropdown.style.display = '';
          return component?.ref?.onKeyDown(event) ?? false;
        },
        // CRITICAL: destroy BOTH the popup element and the ReactRenderer, else the
        // detached react-renderer divs accumulate on every reopen (tiptap issue #6350).
        onExit: () => {
          dropdown?.remove();
          dropdown = null;
          component?.destroy();
          component = null;
        },
      };
    },
  };
}

/**
 * Factory returning the inline atomic Node that represents a `{{variable}}`
 * placeholder, rendered as a chip. `atom: true` makes it delete as a single
 * unit; `renderText` emits `{{key}}` so plain text / clipboard output carries
 * the placeholder.
 *
 * `getProfileVariables` is called on every suggestion query so a stable
 * extension instance still sees the latest per-agent profile variables (the
 * caller wires a ref-backed getter — no extension rebuild on prop change).
 */
export function createVariableMention(getProfileVariables: ProfileVariablesGetter = () => []) {
  const suggestion = buildSuggestion(getProfileVariables);
  return Node.create({
    name: VARIABLE_MENTION_NAME,
    group: 'inline',
    inline: true,
    atom: true,
    selectable: true,
    draggable: true,

    addAttributes() {
      return {
        key: {
          default: null,
          parseHTML: (el) => el.getAttribute('data-variable-key'),
          renderHTML: (attrs) => (attrs.key ? { 'data-variable-key': attrs.key } : {}),
        },
        // null for system + profile variables; a string (possibly empty) for
        // custom variables, which marks the chip as custom and carries its
        // runtime default value.
        default: {
          default: null,
          parseHTML: (el) => el.getAttribute('data-variable-default'),
          renderHTML: (attrs) =>
            attrs.default !== null && attrs.default !== undefined
              ? { 'data-variable-default': attrs.default }
              : {},
        },
      };
    },

    parseHTML() {
      return [{ tag: 'span[data-variable-key]' }];
    },

    renderHTML({ HTMLAttributes }) {
      return ['span', mergeAttributes({ 'data-variable-mention': '' }, HTMLAttributes)];
    },

    renderText({ node }) {
      return variableToken(node.attrs.key, node.attrs.default);
    },

    addNodeView() {
      return ReactNodeViewRenderer(VariableChip);
    },

    addProseMirrorPlugins() {
      return [Suggestion<PromptVariable, PromptVariable>({ editor: this.editor, ...suggestion })];
    },
  });
}

// No default export — every caller must go through `createVariableMention()`
// so they consciously wire a `getProfileVariables` getter (or explicitly opt
// out with `() => []`). Prevents a future contributor from silently getting
// an editor with no profile variables in the picker.
