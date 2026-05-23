'use client';

import { motion } from 'framer-motion';
import { useAtom } from 'jotai';
import { Building2, Crown, Plus, Search, Shield, User } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

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
import { TextInput } from '@/components/shared';
import { getOrganizationDetails } from '@/services/organizationService';
import type { OrganizationDetails, OrganizationUpdatePayload } from '@/types/organization';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface StatChipProps {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}

function StatChip({ label, value, icon: Icon, accent }: StatChipProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
      <div
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1',
          accent,
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="leading-tight">
        <p className="text-[20px] font-semibold tracking-tight">{value}</p>
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

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

  const loadOrgs = useCallback(async () => {
    setLoading(true);
    try {
      await fetchOrgs();
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  }, [fetchOrgs]);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    loadOrgs();
  }, [loadOrgs]);

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

  const orgs = data.organizationList;
  const stats = useMemo(() => {
    const total = orgs.length;
    const owner = orgs.filter((o) => o.role === 'owner').length;
    const admin = orgs.filter((o) => o.role === 'admin').length;
    const member = total - owner - admin;
    return { total, owner, admin, member };
  }, [orgs]);

  const filteredOrgs = useMemo(() => {
    if (!searchQuery) return orgs;
    const q = searchQuery.toLowerCase();
    return orgs.filter(
      (org) => org.name.toLowerCase().includes(q) || org.slug.toLowerCase().includes(q),
    );
  }, [orgs, searchQuery]);

  return (
    <div className="animate-page">
      {/* Header */}
      <motion.div
        className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Organizations</h1>
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            Manage your workspaces and team collaboration
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={handleOpenCreate}>
          New Organization
        </CustomButton>
      </motion.div>

      {/* Stats strip */}
      {!loading && orgs.length > 0 && (
        <motion.div
          className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
          }}
        >
          {[
            {
              label: 'Workspaces',
              value: stats.total,
              icon: Building2,
              accent: 'bg-primary/10 text-primary ring-primary/15',
            },
            {
              label: 'Owner',
              value: stats.owner,
              icon: Crown,
              accent: 'bg-amber-500/10 text-amber-600 ring-amber-500/15',
            },
            {
              label: 'Admin',
              value: stats.admin,
              icon: Shield,
              accent: 'bg-blue-500/10 text-blue-600 ring-blue-500/15',
            },
            {
              label: 'Member',
              value: stats.member,
              icon: User,
              accent: 'bg-muted text-muted-foreground ring-border',
            },
          ].map((s) => (
            <motion.div
              key={s.label}
              variants={{
                hidden: { opacity: 0, y: 8 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
              }}
            >
              <StatChip {...s} />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Search */}
      {orgs.length > 0 && (
        <div className="mb-6 max-w-sm">
          <TextInput
            name="org-search"
            placeholder="Search organizations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="size-4" />}
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
      {!loading && orgs.length === 0 && <OrganizationEmptyState onCreate={handleOpenCreate} />}

      {/* Organization cards */}
      {!loading && filteredOrgs.length > 0 && (
        <motion.div
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.04, delayChildren: 0.15 } },
          }}
        >
          {filteredOrgs.map((org, index) => (
            <motion.div
              key={org.id}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
              }}
            >
              <OrganizationCard
                org={org}
                index={index}
                onEdit={handleOpenEdit}
                onDelete={handleDelete}
              />
            </motion.div>
          ))}

          {/* Create new card */}
          <motion.button
            type="button"
            onClick={handleOpenCreate}
            variants={{
              hidden: { opacity: 0, y: 12 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
            }}
            whileHover={{ y: -2 }}
            className="group relative flex min-h-[150px] cursor-pointer items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-border bg-background/40 transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
          >
            <div className="flex flex-col items-center gap-2 p-8">
              <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 transition-transform group-hover:scale-110">
                <Plus className="size-5 text-primary" />
              </div>
              <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground">
                New Organization
              </span>
            </div>
          </motion.button>
        </motion.div>
      )}

      {/* No results */}
      {!loading && searchQuery && filteredOrgs.length === 0 && orgs.length > 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
            <Search className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-sm text-foreground">
            No organizations matching &ldquo;{searchQuery}&rdquo;
          </p>
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="mt-3 text-[13px] font-medium text-primary hover:underline"
          >
            Clear search
          </button>
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
