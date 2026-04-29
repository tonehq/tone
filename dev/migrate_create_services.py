"""
Migration script: Update existing Service records to match their provider's status.

Run from project root:
    python dev/migrate_create_services.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://neondb_owner:npg_6MIP1wKAkFQh@ep-round-pond-anxl0114-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def migrate():
    db = Session()
    try:
        # Find services whose status doesn't match their provider's status
        rows = db.execute(text("""
            SELECT
                s.id AS service_id,
                s.name AS service_name,
                s.status AS service_status,
                sp.name AS provider_name,
                sp.status AS provider_status
            FROM services s
            JOIN service_providers sp ON sp.id = s.service_provider_id
            WHERE s.status != sp.status
            ORDER BY s.id
        """)).fetchall()

        if not rows:
            print("All services already match their provider's status. Nothing to update.")
            return

        print(f"Found {len(rows)} services with mismatched status.\n")

        for row in rows:
            print(f"  {row.service_name}: {row.service_status} -> {row.provider_status} (provider: {row.provider_name})")

        # Update in one query
        result = db.execute(text("""
            UPDATE services s
            SET status = sp.status,
                updated_at = EXTRACT(EPOCH FROM NOW())::bigint
            FROM service_providers sp
            WHERE sp.id = s.service_provider_id
              AND s.status != sp.status
        """))

        db.commit()
        print(f"\nDone. Updated {result.rowcount} service records.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
