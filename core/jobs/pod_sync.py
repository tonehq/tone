import uuid
from datetime import datetime, timezone
from typing import Dict

from kubernetes import client, config
from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database.session import get_db_context
from core.models.node import Node
from core.models.pod import Pod
from core.utils.pod_identity import parse_ordinal
from shared.config import settings

_MEMORY_UNITS = {
    "Ki": 1024,
    "Mi": 1024 ** 2,
    "Gi": 1024 ** 3,
    "Ti": 1024 ** 4,
    "K": 1000,
    "M": 1000 ** 2,
    "G": 1000 ** 3,
}


def _parse_cpu_to_vcpu(value: str) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    if value.endswith("m"):
        return int(value[:-1]) / 1000.0
    if value.endswith("n"):
        return int(value[:-1]) / 1_000_000_000.0
    return float(value)


def _parse_memory_to_mb(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return 0
    for suffix, multiplier in _MEMORY_UNITS.items():
        if value.endswith(suffix):
            return int(float(value[: -len(suffix)]) * multiplier / (1024 ** 2))
    return int(int(value) / (1024 ** 2))


def sync_pods_and_nodes() -> None:
    config.load_incluster_config()
    core = client.CoreV1Api()

    namespace = settings.POD_SYNC_NAMESPACE
    env = settings.ENVIRONMENT
    prefix = settings.CALL_WORKER_PREFIX
    now = datetime.now(timezone.utc)

    pods = [p for p in core.list_namespaced_pod(namespace).items if p.status.phase == "Running"]
    nodes = core.list_node().items

    pods_per_node: Dict[str, int] = {}
    for pod in pods:
        node_name = pod.spec.node_name
        if node_name:
            pods_per_node[node_name] = pods_per_node.get(node_name, 0) + 1

    with get_db_context() as db:
        for node in nodes:
            name = node.metadata.name
            allocatable = node.status.allocatable or {}
            total_vcpu = _parse_cpu_to_vcpu(allocatable.get("cpu", ""))
            total_ram_mb = _parse_memory_to_mb(allocatable.get("memory", ""))
            count = pods_per_node.get(name, 0)
            vcpu_per_pod = total_vcpu / count if count else None
            ram_per_pod_mb = total_ram_mb / count if count else None
            db.execute(
                pg_insert(Node)
                .values(
                    id=uuid.uuid4(),
                    name=name,
                    environment=env,
                    total_vcpu=total_vcpu,
                    total_ram_mb=total_ram_mb,
                    vcpu_per_pod=vcpu_per_pod,
                    ram_per_pod_mb=ram_per_pod_mb,
                    created_at=now,
                    updated_at=now,
                    last_seen_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "environment": env,
                        "total_vcpu": total_vcpu,
                        "total_ram_mb": total_ram_mb,
                        "vcpu_per_pod": vcpu_per_pod,
                        "ram_per_pod_mb": ram_per_pod_mb,
                        "last_seen_at": now,
                        "updated_at": now,
                    },
                )
            )
        db.flush()

        node_ids = {name: node_id for name, node_id in db.query(Node.name, Node.id).all()}

        for pod in pods:
            name = pod.metadata.name
            node_id = node_ids.get(pod.spec.node_name) if pod.spec.node_name else None
            ordinal = parse_ordinal(name, prefix)
            db.execute(
                pg_insert(Pod)
                .values(
                    id=uuid.uuid4(),
                    name=name,
                    node_id=node_id,
                    ordinal=ordinal,
                    environment=env,
                    created_at=now,
                    updated_at=now,
                    last_seen_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "node_id": node_id,
                        "ordinal": ordinal,
                        "environment": env,
                        "last_seen_at": now,
                        "updated_at": now,
                    },
                )
            )
        db.commit()

    logger.info("pod_sync: synced {} running pods across {} nodes", len(pods), len(nodes))


if __name__ == "__main__":
    sync_pods_and_nodes()
