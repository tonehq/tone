"""Hard-delete an agent (or all agents) and everything created during the agent flow.

Removes:
  - DocumentChunk    (rows for the agent's documents)
  - Document         (rows where agent_id = X)
  - Upload           (rows where agent_id = X)
  - CallLog          (rows where agent_id = X)
  - AgentChannelPhoneNumbers (phone assignments for the agent)
  - AgentConfig      (config row for the agent)
  - AgentChannel     (M2M links — channels themselves are NOT deleted)
  - Agent            (the agent row)

Channels and ChannelPhoneNumber inventory are intentionally left alone — they may
be shared with other agents.

Usage (from project root):
    python dev/delete_agent.py --id 42
    python dev/delete_agent.py --uuid 8c1...e9f
    python dev/delete_agent.py --all
    python dev/delete_agent.py --id 42 --dry-run
    python dev/delete_agent.py --all --yes        # skip confirmation
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------------
# Hardcoded DB URL — leave as None to use the app's default SessionLocal
# (which reads from .env / Infisical). Set this to a full SQLAlchemy URL,
# e.g. "postgresql+psycopg2://user:pass@host:5432/dbname"
# --------------------------------------------------------------------------
# DATABASE_URL = "postgresql://neondb_owner:npg_cKx79ofvRXDm@ep-polished-meadow-a4zo0mrh-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# --------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.session import SessionLocal as _DefaultSessionLocal
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.agent_channel import AgentChannel
from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers
from core.models.call_log import CallLog
from core.models.upload import Upload
from core.models.document import Document, DocumentChunk


def _make_session():
    """Return a session bound to the hardcoded DATABASE_URL if set, else default."""
    if DATABASE_URL:
        engine = create_engine(DATABASE_URL, future=True)
        return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()
    return _DefaultSessionLocal()


def _resolve_agent(db, agent_id: int = None, agent_uuid: str = None):
    q = db.query(Agent)
    if agent_id is not None:
        return q.filter(Agent.id == agent_id).first()
    return q.filter(Agent.uuid == agent_uuid).first()


def _summary(db, agent: Agent):
    """Return counts of related rows that will be deleted for one agent."""
    document_ids = [
        row[0] for row in db.query(Document.id).filter(Document.agent_id == agent.id).all()
    ]
    counts = {
        "document_chunks": db.query(DocumentChunk).filter(
            DocumentChunk.document_id.in_(document_ids)
        ).count() if document_ids else 0,
        "documents": len(document_ids),
        "uploads": db.query(Upload).filter(Upload.agent_id == agent.id).count(),
        "call_logs": db.query(CallLog).filter(CallLog.agent_id == agent.id).count(),
        "agent_channel_phone_numbers": db.query(AgentChannelPhoneNumbers).filter(
            AgentChannelPhoneNumbers.agent_id == agent.id
        ).count(),
        "agent_config": db.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).count(),
        "agent_channels": db.query(AgentChannel).filter(AgentChannel.agent_id == agent.id).count(),
    }
    return counts


def delete_agent(db, agent: Agent) -> dict:
    """Run the full delete for one agent (no commit). Returns deleted counts."""
    deleted = {}

    # Documents/chunks have ON DELETE CASCADE from agent, but we delete them
    # explicitly so we get accurate counts and avoid surprises.
    document_ids = [
        row[0] for row in db.query(Document.id).filter(Document.agent_id == agent.id).all()
    ]
    if document_ids:
        deleted["document_chunks"] = db.query(DocumentChunk).filter(
            DocumentChunk.document_id.in_(document_ids)
        ).delete(synchronize_session=False)
    else:
        deleted["document_chunks"] = 0
    deleted["documents"] = db.query(Document).filter(
        Document.agent_id == agent.id
    ).delete(synchronize_session=False)

    # Break the circular FK between uploads <-> call_logs for this agent's rows
    # (Upload.call_log_id and CallLog.upload_id reference each other).
    db.query(Upload).filter(Upload.agent_id == agent.id).update(
        {Upload.call_log_id: None}, synchronize_session=False
    )

    deleted["call_logs"] = db.query(CallLog).filter(
        CallLog.agent_id == agent.id
    ).delete(synchronize_session=False)
    deleted["uploads"] = db.query(Upload).filter(
        Upload.agent_id == agent.id
    ).delete(synchronize_session=False)

    deleted["agent_channel_phone_numbers"] = db.query(AgentChannelPhoneNumbers).filter(
        AgentChannelPhoneNumbers.agent_id == agent.id
    ).delete(synchronize_session=False)
    deleted["agent_config"] = db.query(AgentConfig).filter(
        AgentConfig.agent_id == agent.id
    ).delete(synchronize_session=False)
    deleted["agent_channels"] = db.query(AgentChannel).filter(
        AgentChannel.agent_id == agent.id
    ).delete(synchronize_session=False)

    db.delete(agent)
    deleted["agent"] = 1
    return deleted


def _print_counts(label: str, counts: dict):
    print(label)
    for k, v in counts.items():
        print(f"  {k}: {v}")


def _aggregate_counts(all_counts: list[dict]) -> dict:
    total: dict = {}
    for c in all_counts:
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
    total["agent"] = len(all_counts)
    return total


def main():
    parser = argparse.ArgumentParser(description="Hard-delete an agent (or all agents) and all related rows.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", type=int, help="Numeric agent id")
    group.add_argument("--uuid", type=str, help="Agent UUID")
    group.add_argument("--all", action="store_true", help="Delete EVERY agent in the database")
    parser.add_argument("--dry-run", action="store_true", help="Show counts only, don't delete")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    db = _make_session()
    if DATABASE_URL:
        # Mask credentials in the printed URL
        safe = DATABASE_URL
        if "@" in safe and "://" in safe:
            scheme, rest = safe.split("://", 1)
            if "@" in rest:
                _, host = rest.split("@", 1)
                safe = f"{scheme}://***@{host}"
        print(f"Using hardcoded DATABASE_URL: {safe}")

    try:
        if args.all:
            agents = db.query(Agent).order_by(Agent.id).all()
            if not agents:
                print("No agents found. Nothing to do.")
                return

            per_agent_counts = []
            print(f"Found {len(agents)} agent(s):")
            for a in agents:
                c = _summary(db, a)
                per_agent_counts.append(c)
                print(f"  - id={a.id} uuid={a.uuid} name={a.name!r}")

            total = _aggregate_counts(per_agent_counts)
            _print_counts("\nTotal rows to delete across all agents:", total)
            print("(Channels and ChannelPhoneNumber inventory are NOT deleted.)")

            if args.dry_run:
                print("\nDry run — no changes made.")
                return

            if not args.yes:
                ans = input(
                    f"\nThis will DELETE ALL {len(agents)} agent(s) and the rows above. Type 'DELETE ALL' to confirm: "
                ).strip()
                if ans != "DELETE ALL":
                    print("Aborted.")
                    return

            grand_total: dict = {}
            for a in agents:
                d = delete_agent(db, a)
                for k, v in d.items():
                    grand_total[k] = grand_total.get(k, 0) + v
            db.commit()
            _print_counts("\nDeleted:", grand_total)
            print("Done.")
            return

        # Single agent
        agent = _resolve_agent(db, agent_id=args.id, agent_uuid=args.uuid)
        if not agent:
            print("Agent not found.")
            sys.exit(1)

        print(f"Agent: id={agent.id} uuid={agent.uuid} name={agent.name!r}")
        counts = _summary(db, agent)
        counts_with_agent = {**counts, "agent": 1}
        _print_counts("Will delete the following row counts:", counts_with_agent)
        print("(Channels and ChannelPhoneNumber inventory are NOT deleted.)")

        if args.dry_run:
            print("\nDry run — no changes made.")
            return

        if not args.yes:
            ans = input("\nProceed with delete? [y/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print("Aborted.")
                return

        deleted = delete_agent(db, agent)
        db.commit()
        _print_counts("\nDeleted:", deleted)
        print("Done.")
    except Exception as e:
        db.rollback()
        print(f"\nError — rolled back. {e!r}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
