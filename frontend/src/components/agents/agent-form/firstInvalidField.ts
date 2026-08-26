import type { FieldErrors } from 'react-hook-form';

/**
 * Walk a react-hook-form `FieldErrors` tree and return the dot-path of the
 * first field with a validation error, or `null` if the tree is empty.
 *
 * RHF stores errors in a shape that mirrors the form values. Leaves are
 * `FieldError` objects with a `message` (and usually a `type` + `ref`).
 * Non-leaves are plain nested objects. We recurse until we hit a leaf so
 * the caller gets a fully-qualified path like `config.llm_settings.temperature`.
 */
export function firstInvalidFieldPath(errors: FieldErrors, prefix = ''): string | null {
  if (!errors || typeof errors !== 'object') return null;

  const record = errors as Record<string, unknown>;
  if ('message' in record || 'ref' in record) return prefix || null;

  for (const key of Object.keys(record)) {
    const value = record[key];
    if (value == null || typeof value !== 'object') continue;
    const path = prefix ? `${prefix}.${key}` : key;
    const found = firstInvalidFieldPath(value as FieldErrors, path);
    if (found) return found;
  }
  return null;
}

/**
 * Map a form-field path to the agent-editor section key that owns it. Used
 * after a save-time validation failure to jump the user to the correct tab
 * before scrolling the field into view.
 */
export function sectionKeyForFieldPath(path: string): string {
  if (path.startsWith('config.llm_settings')) return 'setup';
  if (path.startsWith('config.voice_settings')) return 'voice';
  if (path.startsWith('config.stt_settings')) return 'voice';
  if (
    path.startsWith('config.system_prompt_template') ||
    path.startsWith('config.first_message') ||
    path.startsWith('config.end_call_message') ||
    path.startsWith('config.mode') ||
    path.startsWith('config.workflow_id')
  ) {
    return 'prompt';
  }
  // Basics-level fields (name / description / agent_type / is_active) plus any
  // config field not covered above land on Setup, which hosts Basics + AI.
  return 'setup';
}

/**
 * After a validation failure, scroll the DOM element bound to `path` into
 * view and focus it. Handles the common shapes we render:
 *  - inputs / textareas / selects with a matching `name` attribute
 *  - Radix-based sliders which don't take `name` but sit inside a
 *    container we mark with `aria-invalid`
 *
 * Retries on every animation frame for up to ~1.5s. A same-section scroll
 * lands on the first frame; a cross-section jump has to wait for
 * `router.push` to mount the new page + its lazy children before the target
 * exists in the DOM.
 */
export function scrollToInvalidField(path: string): void {
  if (typeof window === 'undefined') return;

  const escaped = path.replace(/"/g, '\\"');
  const deadline = performance.now() + 1500;

  const attempt = () => {
    const byName = document.querySelector<HTMLElement>(`[name="${escaped}"]`);
    const target = byName ?? document.querySelector<HTMLElement>('[aria-invalid="true"]');
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (typeof target.focus === 'function') {
        try {
          target.focus({ preventScroll: true });
        } catch {
          // Some elements (Radix Slider root) reject focus silently — the
          // scroll is what actually matters for the user; ignore.
        }
      }
      return;
    }
    if (performance.now() < deadline) requestAnimationFrame(attempt);
  };

  requestAnimationFrame(attempt);
}
