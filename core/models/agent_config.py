from sqlalchemy import Column, BigInteger, String, ForeignKey, Text, UniqueConstraint
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSON
from core.database.base import Base
from core.models.base import TimestampModel


class AgentConfig(TimestampModel):
    __tablename__ = 'agent_configs'
    __table_args__ = (
        UniqueConstraint('agent_id', name='agent_config_agent_id_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False)
    
    llm_service_id = Column(BigInteger, ForeignKey('service_providers.id'))
    tts_service_id = Column(BigInteger, ForeignKey('service_providers.id'))
    stt_service_id = Column(BigInteger, ForeignKey('service_providers.id'))
    first_message = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True, default="")
    end_call_message = Column(Text, nullable=True)
    voicemail_message = Column(Text, nullable=True)
    status = Column(String, default="active")
    html_prompt = Column(Text, nullable=True)

    llm_metadata = Column(JSON, nullable=True, default={})
    tts_metadata = Column(JSON, nullable=True, default={})  
    stt_metadata = Column(JSON, nullable=True, default={})
    agent_metadata = Column(JSON, nullable=True, default={})
    description = Column(Text, nullable=True)