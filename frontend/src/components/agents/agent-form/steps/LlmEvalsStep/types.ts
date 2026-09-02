// The selected folder in the sidebar. ``null`` = "All", non-null = a
// folder id (folders are first-class rows). Every scenario belongs to a
// real folder — there is no "Uncategorized" bucket.
export type FolderScope = null | string;

// Sub-tab identity inside the LLM Evals section. Kept as a named union so
// the tab key + the state setter agree on the exact strings — a typo in
// one place fails at compile time instead of silently rendering nothing.
export type LlmEvalsView = 'folders' | 'runs';
