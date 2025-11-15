"""
Database Schemas for WhatsApp-like app

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase of the class name.

Collections:
- User -> "user"
- Chat -> "chat"
- Message -> "message"
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class User(BaseModel):
    """Users collection schema"""
    name: str = Field(..., description="Display name")
    avatar: Optional[str] = Field(None, description="Optional avatar URL")
    status: Optional[str] = Field("Hey there! I am using VibeChat", description="Status message")


class Chat(BaseModel):
    """Chats collection schema"""
    title: Optional[str] = Field(None, description="Optional chat title for groups")
    participants: List[str] = Field(..., description="List of user IDs participating in the chat")
    is_group: bool = Field(False, description="Whether this chat is a group chat")


class Message(BaseModel):
    """Messages collection schema"""
    chat_id: str = Field(..., description="Chat ID this message belongs to")
    sender_id: str = Field(..., description="User ID of the sender")
    content: str = Field(..., description="Message text content")
    type: str = Field("text", description="Message type: text, image, etc.")
