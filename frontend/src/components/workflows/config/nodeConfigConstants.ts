/** Option arrays for the node/edge config forms. Co-located so the form
 * components stay JSX-only and the choices are reusable/testable. */

/** Variable value types the extractor supports. */
export const VAR_TYPE_OPTIONS = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes / No' },
  { value: 'date', label: 'Date' },
];

/** Where a tool node sources its action from. */
export const TOOL_SOURCE_OPTIONS = [
  { value: 'tool', label: 'Tool (webhook / custom)' },
  { value: 'mcp', label: 'MCP server' },
];

/** How an edge condition is evaluated. */
export const CONDITION_TYPE_OPTIONS = [
  { value: 'ai', label: 'AI — plain language (LLM-evaluated)' },
  { value: 'logic', label: 'Logic — Liquid expression (deterministic)' },
];
