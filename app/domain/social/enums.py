"""Social simulation domain enumerations.

These enums define the types for social simulation nodes:
- Memory types (individual vs collective)
- Platform types (WeChat vs Xiaohongshu)
- Simulation status
- Agent states
- Interaction types (for agent interactions)
- Report types (for report generation)
"""

from enum import StrEnum


class MemoryType(StrEnum):
    """Memory classification for agent and collective memory."""

    INDIVIDUAL = "INDIVIDUAL"  # Personal memory belonging to a single agent
    COLLECTIVE = "COLLECTIVE"  # Shared memory across multiple agents
    EPISODIC = "EPISODIC"  # Event-based memory
    SEMANTIC = "SEMANTIC"  # Fact/concept-based memory
    PROCEDURAL = "PROCEDURAL"  # Skill/how-to memory


class PlatformType(StrEnum):
    """Social media platform types for simulation."""

    WECHAT = "WECHAT"  # 微信 - messaging focused
    XIAOHONGSHU = "XIAOHONGSHU"  # 小红书 - content sharing focused


class SimulationStatus(StrEnum):
    """Simulation session lifecycle status."""

    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentState(StrEnum):
    """Agent activity state in simulation."""

    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    INTERACTING = "INTERACTING"
    SLEEPING = "SLEEPING"
    OFFLINE = "OFFLINE"


class EmotionType(StrEnum):
    """Basic emotion categories for agent memory tagging."""

    JOY = "JOY"
    SADNESS = "SADNESS"
    ANGER = "ANGER"
    FEAR = "FEAR"
    SURPRISE = "SURPRISE"
    DISGUST = "DISGUST"
    NEUTRAL = "NEUTRAL"


class SeedSourceType(StrEnum):
    """Source types for reality seeds."""

    URL = "URL"
    DOCUMENT = "DOCUMENT"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class InteractionType(StrEnum):
    """Interaction types for agent-agent and agent-platform interactions."""

    # Content interactions
    POST = "POST"  # Agent creates content
    COMMENT = "COMMENT"  # Agent comments on content
    LIKE = "LIKE"  # Agent likes content
    SHARE = "SHARE"  # Agent shares content
    REPOST = "REPOST"  # Agent reposts content

    # Social interactions
    MESSAGE = "MESSAGE"  # Direct message
    FOLLOW = "FOLLOW"  # Follow another agent
    UNFOLLOW = "UNFOLLOW"  # Unfollow another agent
    FRIEND_REQUEST = "FRIEND_REQUEST"
    ACCEPT_FRIEND = "ACCEPT_FRIEND"
    REJECT_FRIEND = "REJECT_FRIEND"

    # Platform actions
    VIEW = "VIEW"  # View content/profile
    CLICK = "CLICK"  # Click on content/link
    SEARCH = "SEARCH"  # Search for content
    HASHTAG_USE = "HASHTAG_USE"  # Use hashtag in post


class ReportType(StrEnum):
    """Report types for simulation analysis."""

    DAILY_SUMMARY = "DAILY_SUMMARY"  # Daily activity summary
    WEEKLY_ANALYSIS = "WEEKLY_ANALYSIS"  # Weekly deep analysis
    INTERACTION_ANALYSIS = "INTERACTION_ANALYSIS"  # Interaction patterns
    MEMORY_EVOLUTION = "MEMORY_EVOLUTION"  # Memory formation/decay
    NETWORK_ANALYSIS = "NETWORK_ANALYSIS"  # Social network structure
    TOPIC_TRENDING = "TOPIC_TRENDING"  # Topic evolution analysis
    AGENT_BEHAVIOR = "AGENT_BEHAVIOR"  # Individual agent behavior
    FULL_SIMULATION = "FULL_SIMULATION"  # Complete simulation report


class NeedType(StrEnum):
    """Agent need types for demand prediction."""

    SOCIAL_CONNECTION = "SOCIAL_CONNECTION"  # Need for social interaction
    INFORMATION = "INFORMATION"  # Need for information/knowledge
    ENTERTAINMENT = "ENTERTAINMENT"  # Need for entertainment
    SELF_EXPRESSION = "SELF_EXPRESSION"  # Need to express oneself
    RECOGNITION = "RECOGNITION"  # Need for recognition/validation
    UTILITY = "UTILITY"  # Practical/functional need
