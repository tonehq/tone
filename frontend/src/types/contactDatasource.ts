/**
 * ContactDatasource types — mirrors `core/models/datasource.py` `to_dict()` and the
 * datasource router shapes. A datasource feeds contacts into a directory through the
 * sync pipeline. CSV-only at launch (auto-provisioned one-per-directory); `config` is
 * reserved for future REST datasources.
 */

/** The datasource kind. Only `csv` is accepted at launch; `rest` is reserved. */
export type DatasourceType = 'csv' | 'rest';

/** A datasource as returned by the datasource endpoints (`to_dict`). */
export interface ContactDatasource {
  id: string;
  directory_id: string | null;
  name: string;
  type: DatasourceType;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** Body for `POST /contact-datasources` (create; admin/owner). */
export interface CreateDatasourcePayload {
  name: string;
  directory_id?: string | null;
  /** Defaults to `csv` on the backend; only `csv` is currently accepted. */
  type?: DatasourceType;
  config?: Record<string, unknown> | null;
}

/** Extra scoping field for `POST /contact-datasources/list` (on top of paging params). */
export interface ListDatasourcesParams {
  directory_id?: string | null;
}
