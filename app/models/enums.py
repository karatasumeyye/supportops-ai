from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SUPPORT_AGENT = "SUPPORT_AGENT"


class SupportRequestStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_CONTACT = "WAITING_FOR_CONTACT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SupportRequestPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SupportRequestChannel(str, Enum):
    WEB_FORM = "WEB_FORM"
    API = "API"
    MANUAL = "MANUAL"


class MessageAuthorType(str, Enum):
    CONTACT = "CONTACT"
    USER = "USER"
    SYSTEM = "SYSTEM"


class MessageType(str, Enum):
    PUBLIC_REPLY = "PUBLIC_REPLY"
    INTERNAL_NOTE = "INTERNAL_NOTE"
