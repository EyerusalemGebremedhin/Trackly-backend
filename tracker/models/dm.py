from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from database import Base

class DirectConversation(Base):
    __tablename__ = "direct_conversations"
    id = Column(Integer, primary_key=True)
    user_low_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_high_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_low_id", "user_high_id"),)

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("direct_conversations.id"), index=True, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
