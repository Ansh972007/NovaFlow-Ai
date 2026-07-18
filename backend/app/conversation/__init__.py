"""
NovaFlow Enterprise Conversation Platform.

Permanent conversation system for all AI interactions across the platform.
"""

from app.conversation.service import (
    create_conversation,
    get_conversation,
    list_conversations,
    append_message,
    get_messages,
)

__all__ = [
    "create_conversation",
    "get_conversation",
    "list_conversations",
    "append_message",
    "get_messages",
]
