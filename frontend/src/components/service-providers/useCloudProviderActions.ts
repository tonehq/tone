'use client';

import { useAtom } from 'jotai';
import { useCallback, useEffect, useState } from 'react';

import { deleteCloudProviderAtom, upsertCloudProviderAtom } from '@/atoms/ServicesAtom';
import { listCloudProviders } from '@/services/servicesService';
import type { CustomTableSortState } from '@/types/components';
import type { CloudProvider, CloudProviderUpsertPayload } from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const DEFAULT_PAGE_SIZE = 20;

/**
 * List + CRUD orchestration for the Cloud Providers management page. Keeps the
 * page thin: it reads state and renders; all fetching/mutations live here.
 * Reads go through the service layer; writes go through the shared atoms.
 */
export function useCloudProviderActions() {
  const [, upsertCloudProvider] = useAtom(upsertCloudProviderAtom);
  const [, deleteCloudProvider] = useAtom(deleteCloudProviderAtom);

  // ── list state ───────────────────────────────────────────────────────────
  const [rows, setRows] = useState<CloudProvider[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<CustomTableSortState>({ field: 'display_name', order: 'asc' });
  const [loading, setLoading] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = useCallback(() => setReloadToken((t) => t + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const sortBy = `${sort.order === 'desc' ? '-' : ''}${sort.field}`;
    listCloudProviders({
      page,
      page_size: pageSize,
      search: search || undefined,
      sort_by: sortBy,
    })
      .then((res) => {
        if (!active) return;
        setRows(res.rows);
        setTotal(res.total);
      })
      .catch((err) => {
        if (active) handleApiError(err);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [page, pageSize, search, sort, reloadToken]);

  // ── create / edit drawer ───────────────────────────────────────────────────
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<CloudProvider | null>(null);
  const [saving, setSaving] = useState(false);

  const openCreate = useCallback(() => {
    setEditing(null);
    setEditOpen(true);
  }, []);

  const openEdit = useCallback((row: CloudProvider) => {
    setEditing(row);
    setEditOpen(true);
  }, []);

  const closeEdit = useCallback(() => setEditOpen(false), []);

  const submit = useCallback(
    async (payload: CloudProviderUpsertPayload, id?: string) => {
      setSaving(true);
      try {
        await upsertCloudProvider({ cloudProviderId: id, values: payload });
        showToast.success(id ? 'Cloud provider updated' : 'Cloud provider created');
        setEditOpen(false);
        setEditing(null);
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSaving(false);
      }
    },
    [upsertCloudProvider, refresh],
  );

  // ── delete confirmation ────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<CloudProvider | null>(null);
  const [deleting, setDeleting] = useState(false);

  const requestDelete = useCallback((row: CloudProvider) => setDeleteTarget(row), []);
  const closeDelete = useCallback(() => {
    if (!deleting) setDeleteTarget(null);
  }, [deleting]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteCloudProvider(deleteTarget.id);
      showToast.success('Cloud provider deleted');
      setDeleteTarget(null);
      refresh();
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, deleteCloudProvider, refresh]);

  return {
    // list
    rows,
    total,
    page,
    pageSize,
    search,
    sort,
    loading,
    setSearch,
    setPage,
    setPageSize,
    setSort,
    // create / edit
    editOpen,
    editing,
    saving,
    openCreate,
    openEdit,
    closeEdit,
    submit,
    // delete
    deleteTarget,
    deleting,
    requestDelete,
    closeDelete,
    confirmDelete,
  };
}
