'use client';

import { useCallback, useMemo, useState } from 'react';

/** Tri-state a directory parent checkbox can show in the tree. */
export type TreeCheckState = 'checked' | 'unchecked' | 'indeterminate';

/**
 * The assign payload the tree emits: whole-directory picks travel as ids (expanded to
 * their active contacts server-side) and individually-ticked contacts as `contact_ids`,
 * so a directory with thousands of contacts never balloons into thousands of rows.
 */
export interface DirectoryContactSelection {
  directory_ids: string[];
  contact_ids: string[];
}

/** Per-directory info the hook needs to reason about tri-state. */
export interface DirectorySelectionMeta {
  /** Live contact count from the directory list (for the "empty → no-op" rule + tri-state). */
  contactCount: number;
}

/**
 * Selection state machine for the directory→contacts tri-state tree.
 *
 * WHAT: tracks two disjoint selection sets — whole directories (`selectedDirectoryIds`)
 * and individual contacts (`selectedContactIds`) — and derives each directory parent's
 * tri-state (`checked` when the whole directory is picked, `indeterminate` when only some
 * of its loaded children are, else `unchecked`). Toggling a directory selects/clears the
 * whole directory (clearing any of its individually-ticked contacts). Toggling a child
 * peels the directory out of the "whole" set and manages that contact id directly.
 *
 * WHEN: drives `DirectoryContactTree`; the emitted `selection` feeds the assign hook's
 * `{ directory_ids, contact_ids }` body.
 *
 * The hook is agnostic to lazy-loading: `contactIdsByDirectory` is whatever children have
 * been loaded so far, so a not-yet-expanded whole-directory pick still counts correctly.
 */
export function useDirectoryContactTreeSelection() {
  // Directories picked as a whole (sent as `directory_ids`).
  const [selectedDirectoryIds, setSelectedDirectoryIds] = useState<Set<string>>(new Set());
  // Contacts picked individually (sent as `contact_ids`).
  const [selectedContactIds, setSelectedContactIds] = useState<Set<string>>(new Set());

  const isDirectorySelected = useCallback(
    (directoryId: string) => selectedDirectoryIds.has(directoryId),
    [selectedDirectoryIds],
  );

  const isContactSelected = useCallback(
    (contactId: string) => selectedContactIds.has(contactId),
    [selectedContactIds],
  );

  /**
   * Derive a directory's parent-checkbox state. A whole-directory pick is always
   * `checked`; otherwise it's `indeterminate` if any of its loaded contacts are ticked,
   * else `unchecked`. An empty directory can never be indeterminate.
   */
  const getDirectoryState = useCallback(
    (directoryId: string, loadedContactIds: string[]): TreeCheckState => {
      if (selectedDirectoryIds.has(directoryId)) return 'checked';
      const anyChild = loadedContactIds.some((id) => selectedContactIds.has(id));
      return anyChild ? 'indeterminate' : 'unchecked';
    },
    [selectedDirectoryIds, selectedContactIds],
  );

  /**
   * Toggle a whole directory. Selecting it adds the directory id and drops any of its
   * individually-ticked children (they're now covered by the whole-directory pick);
   * deselecting removes the directory id. Empty directories are a no-op.
   */
  const toggleDirectory = useCallback(
    (directoryId: string, loadedContactIds: string[], meta: DirectorySelectionMeta) => {
      if (meta.contactCount <= 0) return; // empty directory → no-op
      setSelectedDirectoryIds((prev) => {
        const next = new Set(prev);
        const willSelect = !next.has(directoryId);
        if (willSelect) next.add(directoryId);
        else next.delete(directoryId);
        // When picking the whole directory, clear its now-redundant child ticks.
        if (willSelect && loadedContactIds.length) {
          setSelectedContactIds((prevContacts) => {
            const nextContacts = new Set(prevContacts);
            for (const id of loadedContactIds) nextContacts.delete(id);
            return nextContacts;
          });
        }
        return next;
      });
    },
    [],
  );

  /**
   * Toggle a single contact. If its directory was picked as a whole, first "explode" that
   * pick into the directory's currently-loaded contact ids so removing one child leaves
   * the rest selected, then flip the target contact.
   */
  const toggleContact = useCallback(
    (contactId: string, directoryId: string, loadedContactIds: string[]) => {
      setSelectedDirectoryIds((prevDirs) => {
        if (!prevDirs.has(directoryId)) return prevDirs;
        // Explode the whole-directory pick into individual child ids.
        setSelectedContactIds((prevContacts) => {
          const next = new Set(prevContacts);
          for (const id of loadedContactIds) next.add(id);
          return next;
        });
        const nextDirs = new Set(prevDirs);
        nextDirs.delete(directoryId);
        return nextDirs;
      });
      setSelectedContactIds((prev) => {
        const next = new Set(prev);
        if (next.has(contactId)) next.delete(contactId);
        else next.add(contactId);
        return next;
      });
    },
    [],
  );

  const clear = useCallback(() => {
    setSelectedDirectoryIds(new Set());
    setSelectedContactIds(new Set());
  }, []);

  const selection: DirectoryContactSelection = useMemo(
    () => ({
      directory_ids: Array.from(selectedDirectoryIds),
      contact_ids: Array.from(selectedContactIds),
    }),
    [selectedDirectoryIds, selectedContactIds],
  );

  /**
   * A rough "N selected" summary. Whole-directory picks contribute their `contactCount`
   * (best-effort, from the meta map); individually-ticked contacts each count as one.
   */
  const countSelected = useCallback(
    (metaByDirectory: Map<string, DirectorySelectionMeta>) => {
      let total = selectedContactIds.size;
      for (const dirId of selectedDirectoryIds) {
        total += metaByDirectory.get(dirId)?.contactCount ?? 0;
      }
      return total;
    },
    [selectedContactIds, selectedDirectoryIds],
  );

  const hasSelection = selectedDirectoryIds.size > 0 || selectedContactIds.size > 0;

  return {
    selection,
    hasSelection,
    isDirectorySelected,
    isContactSelected,
    getDirectoryState,
    toggleDirectory,
    toggleContact,
    clear,
    countSelected,
  };
}

export type UseDirectoryContactTreeSelectionResult = ReturnType<
  typeof useDirectoryContactTreeSelection
>;
