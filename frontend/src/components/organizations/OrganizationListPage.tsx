'use client';

import organizationAtom, {
  createOrganizationAtom,
  deleteOrganizationAtom,
  fetchOrganizationList,
  updateOrganizationAtom,
} from '@/atoms/OrganizationAtom';
import OrganizationCard from '@/components/organizations/OrganizationCard';
import OrganizationCardSkeleton from '@/components/organizations/OrganizationCardSkeleton';
import OrganizationDeleteModal from '@/components/organizations/OrganizationDeleteModal';
import OrganizationEmptyState from '@/components/organizations/OrganizationEmptyState';
import OrganizationUpsertModal from '@/components/organizations/OrganizationUpsertModal';
import type { OrgRow } from '@/components/organizations/constants';
import { CustomButton } from '@/components/shared';
import { Card, CardContent } from '@/components/ui/card';
import { getOrganizationDetails } from '@/services/organizationService';
import type { OrganizationDetails, OrganizationUpdatePayload } from '@/types/organization';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Plus } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

const OrganizationListPage: React.FC = () => {
  const [data] = useAtom(organizationAtom);
  const [, fetchOrgs] = useAtom(fetchOrganizationList);
  const [, createOrg] = useAtom(createOrganizationAtom);
  const [, updateOrg] = useAtom(updateOrganizationAtom);
  const [, deleteOrg] = useAtom(deleteOrganizationAtom);

  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [editOrg, setEditOrg] = useState<OrganizationDetails | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OrgRow | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const init = async () => {
      setLoading(true);
      try {
        await fetchOrgs();
      } catch (err) {
        handleApiError(err);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, []);

  const handleOpenCreate = useCallback(() => {
    setEditOrg(null);
    setModalOpen(true);
  }, []);

  const handleOpenEdit = useCallback(async (row: OrgRow) => {
    try {
      const details = await getOrganizationDetails(row.id);
      setEditOrg(details);
      setModalOpen(true);
    } catch (err) {
      handleApiError(err);
    }
  }, []);

  const handleModalClose = useCallback(() => {
    setModalOpen(false);
    setEditOrg(null);
  }, []);

  const handleModalSubmit = useCallback(
    async (formData: { name: string } | { orgId: string; payload: OrganizationUpdatePayload }) => {
      setModalLoading(true);
      try {
        if ('orgId' in formData) {
          await updateOrg(formData);
          showToast.success('Organization updated successfully');
        } else {
          await createOrg(formData.name);
          showToast.success('Organization created successfully');
        }
        handleModalClose();
      } catch (err) {
        handleApiError(err);
      } finally {
        setModalLoading(false);
      }
    },
    [createOrg, updateOrg, handleModalClose],
  );

  const handleDelete = useCallback((row: OrgRow) => {
    setDeleteTarget(row);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await deleteOrg(deleteTarget.id);
      showToast.success('Organization deleted successfully');
      setDeleteTarget(null);
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeleteLoading(false);
    }
  }, [deleteTarget, deleteOrg]);

  const filteredOrgs = searchQuery
    ? data.organizationList.filter(
        (org) =>
          org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          org.slug.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : data.organizationList;

  return (
    <div className="animate-page h-full overflow-y-auto p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Organizations</h1>
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            Manage your workspaces and team collaboration
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={handleOpenCreate}>
          New Organization
        </CustomButton>
      </div>

      {/* Search */}
      {data.organizationList.length > 0 && (
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search organizations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 w-full max-w-sm rounded-lg border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <OrganizationCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && data.organizationList.length === 0 && (
        <OrganizationEmptyState onCreate={handleOpenCreate} />
      )}

      {/* Organization cards */}
      {!loading && filteredOrgs.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredOrgs.map((org, index) => (
            <OrganizationCard
              key={org.id}
              org={org}
              index={index}
              onEdit={handleOpenEdit}
              onDelete={handleDelete}
            />
          ))}

          {/* Create new card */}
          <Card
            className="group flex cursor-pointer items-center justify-center gap-0 border-dashed py-0 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
            onClick={handleOpenCreate}
          >
            <CardContent className="flex flex-col items-center gap-2 p-8">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 transition-transform group-hover:scale-110">
                <Plus className="size-5 text-primary" />
              </div>
              <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground">
                New Organization
              </span>
            </CardContent>
          </Card>
        </div>
      )}

      {/* No results */}
      {!loading && searchQuery && filteredOrgs.length === 0 && data.organizationList.length > 0 && (
        <div className="flex flex-col items-center justify-center py-16">
          <p className="text-sm text-muted-foreground">
            No organizations matching &ldquo;{searchQuery}&rdquo;
          </p>
        </div>
      )}

      <OrganizationUpsertModal
        open={modalOpen}
        onClose={handleModalClose}
        onSubmit={handleModalSubmit}
        organization={editOrg}
        loading={modalLoading}
      />

      <OrganizationDeleteModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        organizationName={deleteTarget?.name ?? ''}
        loading={deleteLoading}
      />
    </div>
  );
};

export default OrganizationListPage;
