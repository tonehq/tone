import json
from types import SimpleNamespace
from unittest import mock

import httpx
import pytest
from turbopuffer import NotFoundError
from turbopuffer.types import Row

from core.services.rag import factory
from core.services.rag.errors import VectorStoreUnavailableError
from core.services.rag.types import VectorRecord
from core.services.rag.vector_stores import turbopuffer_store
from core.services.rag.vector_stores.turbopuffer_store import (
    RESULT_ATTRIBUTES,
    SCHEMA,
    TurbopufferVectorStore,
    shared_client,
)

ORG = "11111111-1111-1111-1111-111111111111"
RUN = "22222222-2222-2222-2222-222222222222"
RUN_2 = "55555555-5555-5555-5555-555555555555"
UPLOAD = "33333333-3333-3333-3333-333333333333"
KB = "44444444-4444-4444-4444-444444444444"
NAMESPACE = f"tone-kb-{ORG}-3"


class FakeNamespace:
    def __init__(self, name, client):
        self.name = name
        self.client = client

    def write(self, **kwargs):
        if self.client.write_error:
            raise self.client.write_error
        self.client.writes.append((self.name, kwargs))
        return SimpleNamespace(rows_affected=len(kwargs.get("upsert_rows") or []))

    def query(self, **kwargs):
        self.client.queries.append((self.name, kwargs))
        if self.name in self.client.missing:
            request = httpx.Request("POST", "http://turbopuffer.test")
            raise NotFoundError("missing", response=httpx.Response(404, request=request), body=None)
        return SimpleNamespace(rows=list(self.client.rows.get(self.name, [])))


class FakeClient:
    def __init__(self):
        self.writes = []
        self.queries = []
        self.rows = {}
        self.missing = set()
        self.write_error = None

    def namespace(self, name):
        return FakeNamespace(name, self)


def record(index, text="chunk", dims=3):
    return VectorRecord(
        text=text,
        embedding=[0.1] * dims,
        metadata={
            "organization_id": ORG,
            "upload_id": UPLOAD,
            "ingestion_run_id": RUN,
            "knowledge_base_id": KB,
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_dimensions": dims,
            "chunk_index": index,
            "chunk_metadata": {"page": index},
        },
    )


def fake_chunks(db, records):
    return [
        SimpleNamespace(
            id=f"chunk-{r.metadata['chunk_index']}",
            organization_id=ORG,
            upload_id=UPLOAD,
            ingestion_run_id=RUN,
            chunk_index=r.metadata["chunk_index"],
        )
        for r in records
    ]


def row(chunk_id, dist, index, metadata=None):
    return Row.from_dict(
        {
            "id": chunk_id,
            "$dist": dist,
            "upload_id": UPLOAD,
            "chunk_index": index,
            "ingestion_run_id": RUN,
            "chunk_text": f"text-{index}",
            "chunk_metadata": json.dumps(metadata) if metadata is not None else None,
        }
    )


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def store(client):
    return TurbopufferVectorStore(client=client, session=mock.MagicMock())


def test_registered_in_factory():
    assert factory.VECTOR_STORES["turbopuffer"] is TurbopufferVectorStore
    assert "turbopuffer" not in factory.DB_BACKED_STORES
    assert "pgvector" in factory.DB_BACKED_STORES


def test_missing_credentials_fail_fast():
    with mock.patch.object(turbopuffer_store.settings, "TURBOPUFFER_API_KEY", ""):
        with pytest.raises(VectorStoreUnavailableError):
            TurbopufferVectorStore()


def test_shared_client_is_reused_per_key_and_region():
    turbopuffer_store._clients.clear()
    with mock.patch.object(turbopuffer_store, "Turbopuffer") as ctor:
        ctor.side_effect = lambda **kwargs: SimpleNamespace(kwargs=kwargs)
        first = shared_client("key-a", "gcp-us-central1")
        second = shared_client("key-a", "gcp-us-central1")
        other = shared_client("key-a", "aws-us-east-1")
    assert first is second
    assert other is not first
    assert ctor.call_count == 2
    assert first.kwargs == {
        "api_key": "key-a",
        "region": "gcp-us-central1",
        "timeout": 20.0,
        "max_retries": 2,
    }
    turbopuffer_store._clients.clear()


def test_invalid_namespace_prefix_rejected(client):
    with pytest.raises(ValueError):
        TurbopufferVectorStore(client=client, namespace_prefix="bad prefix!")


def test_add_writes_rows_to_org_and_dims_namespace(store, client):
    records = [record(0, "alpha"), record(1, "beta")]

    with mock.patch.object(turbopuffer_store, "insert_chunk_rows", side_effect=fake_chunks) as inserted:
        assert store.add(records) == 2

    inserted.assert_called_once_with(store._session, records)
    name, kwargs = client.writes[0]
    assert name == NAMESPACE
    assert kwargs["distance_metric"] == "cosine_distance"
    assert kwargs["schema"] is SCHEMA
    rows = kwargs["upsert_rows"]
    assert [r["id"] for r in rows] == ["chunk-0", "chunk-1"]
    assert rows[0]["vector"] == [0.1, 0.1, 0.1]
    assert rows[1]["chunk_text"] == "beta"
    assert json.loads(rows[1]["chunk_metadata"]) == {"page": 1}
    assert rows[0]["ingestion_run_id"] == RUN
    assert rows[0]["knowledge_base_id"] == KB
    assert rows[0]["embedding_model"] == "text-embedding-3-small"
    store._session.commit.assert_not_called()


def test_add_rolls_back_own_session_when_remote_write_fails(client):
    db = mock.MagicMock()
    client.write_error = RuntimeError("turbopuffer down")
    store = TurbopufferVectorStore(client=client)

    with mock.patch.object(turbopuffer_store, "get_db_context") as ctx, \
            mock.patch.object(turbopuffer_store, "insert_chunk_rows", side_effect=fake_chunks):
        ctx.return_value.__enter__.return_value = db
        with pytest.raises(RuntimeError):
            store.add([record(0)])

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_add_commits_own_session(client):
    db = mock.MagicMock()
    store = TurbopufferVectorStore(client=client)

    with mock.patch.object(turbopuffer_store, "get_db_context") as ctx, \
            mock.patch.object(turbopuffer_store, "insert_chunk_rows", side_effect=fake_chunks):
        ctx.return_value.__enter__.return_value = db
        assert store.add([record(0)]) == 1

    db.commit.assert_called_once()


def test_add_empty_is_noop(store, client):
    assert store.add([]) == 0
    assert client.writes == []


def test_query_scopes_runs_and_maps_rows(store, client):
    client.rows[NAMESPACE] = [row("chunk-1", 0.2, 1, {"page": 1}), row("chunk-0", 0.1, 0)]
    filters = {"agent_id": "agent-1", "ingestion_run_id": RUN, "embedding_provider": "openai"}

    with mock.patch.object(turbopuffer_store, "scoped_runs", return_value=[(RUN, ORG, 3)]) as scoped:
        results = store.query([0.1, 0.1, 0.1], top_k=5, filters=filters, query_text="hello")

    assert scoped.call_args.args[1]["embedding_dimensions"] == 3
    assert scoped.call_args.args[1]["agent_id"] == "agent-1"
    name, kwargs = client.queries[0]
    assert name == NAMESPACE
    assert kwargs["rank_by"] == ("vector", "ANN", [0.1, 0.1, 0.1])
    assert kwargs["filters"] == ("ingestion_run_id", "In", [RUN])
    assert kwargs["top_k"] == 5
    assert kwargs["include_attributes"] == RESULT_ATTRIBUTES
    assert [r.id for r in results] == ["chunk-0", "chunk-1"]
    assert results[0].text == "text-0"
    assert results[0].score == 0.1
    assert results[0].metadata == {
        "upload_id": UPLOAD,
        "chunk_index": 0,
        "chunk_metadata": {},
        "ingestion_run_id": RUN,
    }
    assert results[1].metadata["chunk_metadata"] == {"page": 1}


def test_query_without_matching_runs_skips_remote_call(store, client):
    with mock.patch.object(turbopuffer_store, "scoped_runs", return_value=[]):
        assert store.query([0.1, 0.1, 0.1], filters={"upload_id": UPLOAD}) == []
    assert client.queries == []


def test_query_missing_namespace_returns_empty(store, client):
    client.missing.add(NAMESPACE)
    with mock.patch.object(turbopuffer_store, "scoped_runs", return_value=[(RUN, ORG, 3)]):
        assert store.query([0.1, 0.1, 0.1], filters={"ingestion_run_id": RUN}) == []


def test_query_merges_runs_sharing_a_namespace_and_truncates(store, client):
    client.rows[NAMESPACE] = [row("c", 0.3, 2), row("a", 0.1, 0), row("b", 0.2, 1)]

    with mock.patch.object(
        turbopuffer_store, "scoped_runs", return_value=[(RUN, ORG, 3), (RUN_2, ORG, 3)]
    ):
        results = store.query([0.1, 0.1, 0.1], top_k=2, filters={"agent_id": "agent-1"})

    assert len(client.queries) == 1
    assert client.queries[0][1]["filters"] == ("ingestion_run_id", "In", [RUN, RUN_2])
    assert [r.id for r in results] == ["a", "b"]


def test_delete_purges_each_namespace_then_chunk_rows(store, client):
    runs = [(RUN, ORG, 3), (RUN_2, ORG, 1536)]

    with mock.patch.object(turbopuffer_store, "runs_for_filters", return_value=runs), \
            mock.patch.object(turbopuffer_store, "chunk_rows_query") as chunk_rows:
        chunk_rows.return_value.delete.return_value = 7
        assert store.delete(filters={"upload_id": UPLOAD, "organization_id": ORG}) == 7

    assert client.writes == [
        (NAMESPACE, {"delete_by_filter": ("ingestion_run_id", "In", [RUN])}),
        (f"tone-kb-{ORG}-1536", {"delete_by_filter": ("ingestion_run_id", "In", [RUN_2])}),
    ]
    chunk_rows.return_value.delete.assert_called_once_with(synchronize_session=False)
    store._session.commit.assert_not_called()


def test_delete_requires_upload_or_run(store):
    with pytest.raises(ValueError):
        store.delete(filters={"organization_id": ORG})


def test_count_reads_chunk_rows(store):
    with mock.patch.object(turbopuffer_store, "chunk_rows_query") as chunk_rows:
        chunk_rows.return_value.count.return_value = 4
        assert store.count(filters={"upload_id": UPLOAD}) == 4
    assert chunk_rows.call_args.args[1] == {"upload_id": UPLOAD}
