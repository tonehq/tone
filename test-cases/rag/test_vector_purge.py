from unittest import mock

import pytest

from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.services.ingestion_run_service import IngestionRunService
from core.services.rag.errors import EmbeddingCompatibilityError, VectorStoreUnavailableError
from core.services.rag.types import VectorRecord
from core.services.rag.vector_stores.chunk_rows import chunk_rows_query, insert_chunk_rows
from core.services.upload_service import UploadService


def _run(store, ref=None):
    return mock.Mock(id="r1", organization_id="o1", vector_store=store, vector_store_ref=ref)


def _record(dims=3, vector_dims=3, **overrides):
    metadata = {
        "organization_id": "o1",
        "upload_id": "u1",
        "ingestion_run_id": "r1",
        "chunk_index": 2,
        "embedding_dimensions": dims,
        "chunk_metadata": {"page": 2},
    }
    metadata.update(overrides)
    return VectorRecord(text="body", embedding=[0.5] * vector_dims, metadata=metadata)


def test_insert_chunk_rows_builds_rows_and_flushes():
    db = mock.MagicMock()

    rows = insert_chunk_rows(db, [_record()])

    assert len(rows) == 1
    assert isinstance(rows[0], KnowledgeBaseChunk)
    assert rows[0].chunk_text == "body"
    assert rows[0].chunk_index == 2
    assert rows[0].chunk_metadata == {"page": 2}
    db.add_all.assert_called_once_with(rows)
    db.flush.assert_called_once()


def test_insert_chunk_rows_rejects_dimension_mismatch():
    with pytest.raises(EmbeddingCompatibilityError):
        insert_chunk_rows(mock.MagicMock(), [_record(dims=3, vector_dims=4)])


def test_insert_chunk_rows_requires_identity_keys():
    with pytest.raises(ValueError, match="upload_id"):
        insert_chunk_rows(mock.MagicMock(), [_record(upload_id=None)])


def test_chunk_rows_query_applies_only_present_filters():
    db = mock.MagicMock()
    chunk_rows_query(db, {"upload_id": "u1", "organization_id": None})
    assert db.query.return_value.filter.call_count == 1


def test_purge_skips_db_backed_stores():
    with mock.patch("core.services.ingestion_run_service.get_vector_store") as get_store:
        IngestionRunService.purge_remote_vectors(mock.MagicMock(), [_run("pgvector")])
    get_store.assert_not_called()


def test_purge_deletes_remote_vectors_with_caller_session():
    db = mock.MagicMock()
    with mock.patch("core.services.ingestion_run_service.get_vector_store") as get_store:
        IngestionRunService.purge_remote_vectors(
            db, [_run("turbopuffer", {"namespace_prefix": "kb"})]
        )
    get_store.assert_called_once_with("turbopuffer", session=db, namespace_prefix="kb")
    get_store.return_value.delete.assert_called_once_with(
        filters={"ingestion_run_id": "r1", "organization_id": "o1"}
    )


def test_purge_skips_runs_whose_store_is_not_configured():
    db = mock.MagicMock()
    configured = mock.MagicMock()
    with mock.patch("core.services.ingestion_run_service.get_vector_store") as get_store:
        get_store.side_effect = [VectorStoreUnavailableError("no credentials"), configured]
        IngestionRunService.purge_remote_vectors(db, [_run("turbopuffer"), _run("turbopuffer")])
    assert get_store.call_count == 2
    configured.delete.assert_called_once()


def test_delete_run_purges_before_deleting():
    db = mock.MagicMock()
    run = _run("turbopuffer")
    db.query.return_value.filter.return_value.first.return_value = run

    with mock.patch.object(IngestionRunService, "purge_remote_vectors") as purge:
        IngestionRunService.delete_run(db, "r1", org_id="o1")

    purge.assert_called_once_with(db, [run])
    db.delete.assert_called_once_with(run)
    db.commit.assert_called_once()


def test_delete_runs_for_upload_purges_then_bulk_deletes():
    db = mock.MagicMock()
    runs = [_run("turbopuffer")]
    scoped = db.query.return_value.filter.return_value
    scoped.all.return_value = runs
    scoped.delete.return_value = 1

    with mock.patch.object(IngestionRunService, "purge_remote_vectors") as purge:
        assert IngestionRunService.delete_runs_for_upload(db, upload_id="u1", org_id="o1") == 1

    purge.assert_called_once_with(db, runs)
    scoped.delete.assert_called_once_with(synchronize_session=False)
    db.commit.assert_called_once()


def test_delete_upload_purges_remote_vectors_first():
    service = UploadService(mock.MagicMock(), org_id="o1")
    upload = mock.Mock(file_path=None)
    runs = [_run("turbopuffer")]
    service.db.query.return_value.filter.return_value.all.return_value = runs

    with mock.patch.object(service, "_get_org_upload", return_value=upload), \
            mock.patch.object(IngestionRunService, "purge_remote_vectors") as purge:
        service.delete_upload("u1")

    purge.assert_called_once_with(service.db, runs)
    service.db.delete.assert_called_once_with(upload)
    service.db.commit.assert_called_once()
