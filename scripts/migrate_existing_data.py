import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from core.database.base import engine
from core.database.session import SessionLocal
from core.models.organization import Organization
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.agent_channel import AgentChannel
from core.models.channel import Channel
from core.models.channel_phone_numbers import ChannelPhoneNumbers
from core.models.member import Member
from core.models.organization_invite import OrganizationInvite
from core.models.organization_access_request import OrganizationAccessRequest
from core.models.api_key import ApiKey
from core.models.service import Service
from core.models.generated_api_key import GeneratedApiKey
from core.models.enums import OrganizationStatus
import uuid
import time


DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def migrate_existing_data():
    db = SessionLocal()

    try:
        existing_org = db.query(Organization).filter(Organization.id == DEFAULT_ORG_ID).first()

        if not existing_org:
            print("Creating default organization...")
            default_org = Organization(
                id=DEFAULT_ORG_ID,
                name="Default Organization",
                slug="default",
                description="Default organization for existing data",
                status=OrganizationStatus.ACTIVE,
                created_by=1,
                subscription_plan="free",
                subscription_status="active",
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )
            db.add(default_org)
            db.commit()
            print(f"Created default organization: {DEFAULT_ORG_ID}")
        else:
            print(f"Default organization already exists: {DEFAULT_ORG_ID}")

        tables_to_update = [
            (Agent, "agents"),
            (AgentConfig, "agent_configs"),
            (AgentChannel, "agent_channels"),
            (Channel, "channels"),
            (ChannelPhoneNumbers, "channel_phone_numbers"),
            (Member, "members"),
            (OrganizationInvite, "organization_invites"),
            (OrganizationAccessRequest, "organization_access_requests"),
            (ApiKey, "api_keys"),
            (Service, "services"),
            (GeneratedApiKey, "generated_api_keys"),
        ]

        for model, table_name in tables_to_update:
            count = db.query(model).filter(model.organization_id == None).count()
            if count > 0:
                print(f"Updating {count} records in {table_name}...")
                db.query(model).filter(model.organization_id == None).update(
                    {"organization_id": DEFAULT_ORG_ID},
                    synchronize_session=False
                )
                db.commit()
                print(f"Updated {table_name}")
            else:
                print(f"No records to update in {table_name}")

        print("\nMigration complete!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_existing_data()
