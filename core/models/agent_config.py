from sqlalchemy import Column, BigInteger, String, ForeignKey, Text, UniqueConstraint
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSON
from core.models.base import OrgScopedModel


class AgentConfig(OrgScopedModel):
    __tablename__ = 'agent_configs'
    __table_args__ = (
        UniqueConstraint('organization_id', 'agent_id', name='agent_config_org_agent_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False)
    
    llm_account_id = Column(BigInteger, ForeignKey('accounts.id'))
    tts_account_id = Column(BigInteger, ForeignKey('accounts.id'))
    stt_account_id = Column(BigInteger, ForeignKey('accounts.id'))
    llm_model_instance_id = Column(BigInteger, ForeignKey('model_instance.id', ondelete='SET NULL'), nullable=True)
    tts_model_instance_id = Column(BigInteger, ForeignKey('model_instance.id', ondelete='SET NULL'), nullable=True)
    stt_model_instance_id = Column(BigInteger, ForeignKey('model_instance.id', ondelete='SET NULL'), nullable=True)
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