import { useEffect, useRef } from 'react';

/**
 * Tri-state "select all" checkbox helper. A native `<input type="checkbox">`
 * cannot express the `indeterminate` (some-but-not-all selected) state through a
 * prop, so it has to be set imperatively via a ref. This centralizes that ref +
 * effect and the `allSelected`/`someSelected` derivation that the eval selection
 * tables previously each hand-rolled.
 *
 * @param total         number of selectable rows currently in view
 * @param selectedCount how many of those rows are currently selected
 * @returns `ref` to attach to the header checkbox, plus `allSelected` (bind to
 *   `checked`) and `someSelected` (the indeterminate state, applied to the ref).
 */
export function useIndeterminateCheckbox(total: number, selectedCount: number) {
  const ref = useRef<HTMLInputElement | null>(null);
  const allSelected = total > 0 && selectedCount === total;
  const someSelected = selectedCount > 0 && selectedCount < total;

  useEffect(() => {
    if (ref.current) ref.current.indeterminate = someSelected;
  }, [someSelected]);

  return { ref, allSelected, someSelected };
}
