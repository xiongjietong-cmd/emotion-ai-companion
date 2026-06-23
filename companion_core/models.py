from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    role: str
    content: str
    created_at: str | None = None


class MemoryItem(BaseModel):
    key: str
    value: str
    type: str = "episodic"
    emotion: str = ""
    salience: float = 0.5
    last_used_at: str | None = None


class ReplyRequest(BaseModel):
    bot_id: str
    user_key: str
    channel: str = "web"
    text: str
    recent_messages: list[MessageItem] = Field(default_factory=list)
    conversation_summary: dict = Field(default_factory=dict)
    memories: list[MemoryItem] = Field(default_factory=list)
    relationship: dict = Field(default_factory=dict)
    personality_config: dict = Field(default_factory=dict)
    provider_config: dict = Field(default_factory=dict)
    conversation_state: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)


class ReplyResponse(BaseModel):
    reply: str
    reply_parts: list[str] = Field(default_factory=list)
    relationship_delta: dict
    memory_candidates: list[dict]
    director_goal: dict
    judge: dict
