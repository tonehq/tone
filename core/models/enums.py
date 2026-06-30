import enum


class Role(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    OBSERVER = "observer"


class WorkflowNodeType(str, enum.Enum):
    """Node types for the visual workflow builder (Vapi-aligned + a decision router)."""
    CONVERSATION = "conversation"
    TOOL = "tool"
    TRANSFER_CALL = "transferCall"
    END_CALL = "endCall"
    DECISION = "decision"
    API_REQUEST = "apiRequest"


class EdgeConditionType(str, enum.Enum):
    """How an edge condition is evaluated to route between nodes."""
    AI = "ai"        # plain-language, LLM-evaluated
    LOGIC = "logic"  # deterministic LiquidJS boolean over the variable context


class AgentConfigMode(str, enum.Enum):
    """Conversation-flow driver for an agent config."""
    PROMPT = "prompt"      # single system-prompt assistant (default / today's behavior)
    WORKFLOW = "workflow"  # the assigned workflow graph drives turn-to-turn flow


class WorkflowStatus(str, enum.Enum):
    """Lifecycle status of a workflow container."""
    DRAFT = "draft"          # never published
    PUBLISHED = "published"  # has at least one published version
