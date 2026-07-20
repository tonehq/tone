/**
 * Barrel for the reusable Contact Directories building blocks (F0). Directory pages
 * (F2–F5, F7) and the Agent Contacts tab (F6) import from here so there is one canonical
 * path for every shared piece — see the FE reusable-components catalog in the plan.
 */
export { default as ContactsTable } from './ContactsTable';
export type { ContactsTableProps } from './ContactsTable';

export { default as SchemaDrivenContactForm } from './SchemaDrivenContactForm';
export type { SchemaDrivenContactFormProps } from './SchemaDrivenContactForm';

export {
  buildContactFormSchema,
  buildContactMetadataSchema,
  phoneNumberSchema,
} from './buildContactFormSchema';
export type { ContactFormValues } from './buildContactFormSchema';

export { default as SchemaFieldsEditor } from './SchemaFieldsEditor';
export type { SchemaFieldsEditorProps } from './SchemaFieldsEditor';

export { default as SyncContactsModal } from './SyncContactsModal';
export type { SyncContactsModalProps } from './SyncContactsModal';

export { default as SyncStatusChip } from './SyncStatusChip';

export { useSyncStatusPolling } from './useSyncStatusPolling';
export type { UseSyncStatusPollingResult } from './useSyncStatusPolling';

export { default as ConfirmDeleteModal } from './ConfirmDeleteModal';
export type { ConfirmDeleteModalProps } from './ConfirmDeleteModal';

export { default as AssignContactsModal } from './AssignContactsModal';
export type { AssignContactsModalProps } from './AssignContactsModal';

export { default as DirectoryContactTree } from './DirectoryContactTree';
export type { DirectoryContactTreeProps } from './DirectoryContactTree';

export { useDirectoryContactTreeSelection } from './useDirectoryContactTreeSelection';
export type {
  DirectoryContactSelection,
  DirectorySelectionMeta,
  TreeCheckState,
  UseDirectoryContactTreeSelectionResult,
} from './useDirectoryContactTreeSelection';
