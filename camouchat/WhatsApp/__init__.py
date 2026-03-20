"""
WhatsApp platform integration for CamouChat.

Provides chat processing, message handling, media operations,
and human-like interaction capabilities for WhatsApp Web automation.
"""

from .chat_processor import ChatProcessor
from .login import Login
from .message_processor import MessageProcessor
from .media_capable import MediaCapable
from .human_interaction_controller import HumanInteractionController
from .web_ui_config import WebSelectorConfig
from .reply_capable import ReplyCapable

__all__ = [
    "ChatProcessor",
    "Login",
    "MessageProcessor",
    "MediaCapable",
    "HumanInteractionController",
    "ReplyCapable",
    "WebSelectorConfig",
]
