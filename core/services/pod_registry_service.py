import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.models.node import Node
from core.models.pod import Pod
from core.utils.pod_identity import get_served_by, parse_ordinal


def resolve_pod_id(db: Session) -> Optional[uuid.UUID]:
    served_by = get_served_by()
    pod_name = served_by.get("pod")
    if not pod_name:
        return None

    now = datetime.now(timezone.utc)
    node_name = served_by.get("node")
    deployment = served_by.get("deployment")
    env = served_by.get("environment")

    node_id = None
    if node_name:
        db.execute(
            pg_insert(Node)
            .values(id=uuid.uuid4(), name=node_name, environment=env, created_at=now, updated_at=now, last_seen_at=now)
            .on_conflict_do_update(
                index_elements=["name"],
                set_={"environment": env, "last_seen_at": now, "updated_at": now},
            )
        )
        db.flush()
        node = db.query(Node).filter(Node.name == node_name).first()
        node_id = node.id if node else None

    ordinal = parse_ordinal(pod_name, deployment)
    db.execute(
        pg_insert(Pod)
        .values(
            id=uuid.uuid4(),
            name=pod_name,
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
    db.flush()
    pod = db.query(Pod).filter(Pod.name == pod_name).first()
    return pod.id if pod else None
