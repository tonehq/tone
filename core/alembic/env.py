import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.base import Base
from core.config import settings

from core.models.user import User
from core.models.member import Member
from core.models.organization_invite import OrganizationInvite
from core.models.organization_access_request import OrganizationAccessRequest
from core.models.email_verification import EmailVerification
from core.models.password_reset import PasswordReset
from core.models.service_provider import ServiceProvider
from core.models.api_key import ApiKey
from core.models.service import Service
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.agent_phone_numbers import AgentPhoneNumbers
from core.models.models import Model

config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
