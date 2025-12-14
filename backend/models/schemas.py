from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.1:8b"

class ChatResponse(BaseModel):
    response: str
    model: str

class UserProfileBase(BaseModel):
    key: str
    value: str
    category: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    updated_at: datetime
    class Config:
        from_attributes = True

class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    status: str = 'active'
    progress: int = 0

class GoalCreate(GoalBase):
    pass

class Goal(GoalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    user_message: str
    assistant_message: str
    consolidated: bool = False
    importance_score: Optional[float] = None

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    timestamp: datetime
    class Config:
        from_attributes = True
