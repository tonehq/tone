'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

interface UnsavedChangesGuardOptions {
  /**
   * Return true for destinations that should NOT trigger the guard — i.e.
   * navigations that stay "inside" the current editor and don't lose state
   * (e.g. switching sections in the agent editor, which all share one
   * persisted form). Only navigations that leave the editor prompt.
   */
  isInternalNavigation?: (dest: string) => boolean;
}

interface UnsavedChangesGuard {
  /** True when an attempted navigation is waiting on user confirmation. */
  promptOpen: boolean;
  /** Run an arbitrary action through the guard. When dirty, it's held until
   * the user confirms via {@link confirmLeave}; when clean, it runs now. */
  guardedAction: (action: () => void) => void;
  /** Confirm and run the pending action. */
  confirmLeave: () => void;
  /** Dismiss the prompt and keep the user on the page. */
  cancelLeave: () => void;
}

const SENTINEL_STATE = { __unsavedGuard: true };

/**
 * Guards an in-flight form against losing unsaved changes.
 *
 * Coverage:
 * - Any `<a>` click that targets the same origin (sidebar, header, every
 *   Next.js `<Link>`): a capture-phase click handler runs before Next's
 *   Link onClick. We call `preventDefault()`; Next's Link checks
 *   `defaultPrevented` and bails out without navigating.
 * - Browser back / forward: a sentinel `history.pushState` plus a
 *   `popstate` handler that re-pushes the URL and queues the back action.
 * - Browser refresh / tab close: `beforeunload` (native dialog — the
 *   platform doesn't let us replace this with custom UI).
 * - Explicit "Back" / "Cancel" buttons: wrap them in {@link guardedAction}.
 * - Intentional post-save / post-delete redirects: reset the form (so
 *   `isDirty` is false) before calling `router.push`.
 */
export function useUnsavedChangesGuard(
  isDirty: boolean,
  options?: UnsavedChangesGuardOptions,
): UnsavedChangesGuard {
  const router = useRouter();
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  const skipNextPopRef = useRef(false);
  // Kept in a ref so the click handler always sees the latest predicate
  // without re-subscribing the capture-phase listener.
  const isInternalRef = useRef(options?.isInternalNavigation);
  isInternalRef.current = options?.isInternalNavigation;

  // ── beforeunload (refresh / tab close) ───────────────────────────────────
  useEffect(() => {
    if (!isDirty) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  // ── click intercept on any same-origin <a> ──────────────────────────────
  useEffect(() => {
    if (!isDirty) return;

    const handler = (event: MouseEvent) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = (event.target as HTMLElement | null)?.closest('a');
      if (!anchor) return;
      if (anchor.target && anchor.target !== '_self') return;
      if (anchor.hasAttribute('download')) return;
      const rawHref = anchor.getAttribute('href');
      if (!rawHref || rawHref.startsWith('#')) return;

      let url: URL;
      try {
        url = new URL(anchor.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;

      const dest = url.pathname + url.search + url.hash;
      const current = window.location.pathname + window.location.search;
      if (dest === current) return;

      // In-editor navigation (e.g. switching agent sections) keeps the same
      // persisted form, so it should pass through without prompting.
      if (isInternalRef.current?.(dest)) return;

      // Capture-phase + preventDefault keeps Next.js Link from navigating
      // (it short-circuits on defaultPrevented).
      event.preventDefault();
      event.stopPropagation();
      setPendingAction(() => () => router.push(dest));
    };

    document.addEventListener('click', handler, true);
    return () => document.removeEventListener('click', handler, true);
  }, [isDirty, router]);

  // ── popstate (browser back / forward) ────────────────────────────────────
  useEffect(() => {
    if (!isDirty) return;
    window.history.pushState(SENTINEL_STATE, '');

    const handler = () => {
      if (skipNextPopRef.current) {
        skipNextPopRef.current = false;
        return;
      }
      window.history.pushState(SENTINEL_STATE, '');
      setPendingAction(() => () => {
        skipNextPopRef.current = true;
        window.history.go(-2);
      });
    };

    window.addEventListener('popstate', handler);
    return () => {
      window.removeEventListener('popstate', handler);
      // We intentionally do NOT call history.back() here even if the sentinel
      // is on top. Doing so races with `router.push` from inside save/delete
      // (Next.js's pushState lands in a microtask), and we'd undo the redirect
      // the user just performed. Leaving the sentinel costs one extra back
      // press in history at worst — a fine trade for not breaking navigation.
    };
  }, [isDirty]);

  const guardedAction = useCallback(
    (action: () => void) => {
      if (isDirty) {
        setPendingAction(() => action);
      } else {
        action();
      }
    },
    [isDirty],
  );

  const confirmLeave = useCallback(() => {
    pendingAction?.();
    setPendingAction(null);
  }, [pendingAction]);

  const cancelLeave = useCallback(() => setPendingAction(null), []);

  return {
    promptOpen: pendingAction !== null,
    guardedAction,
    confirmLeave,
    cancelLeave,
  };
}
