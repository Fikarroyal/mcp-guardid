from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[self.value]


class RoleName(str, Enum):
    VIEWER = "Viewer"
    IT_SUPPORT = "IT Support"
    NETWORK_ENGINEER = "Network Engineer"
    DATABASE_ADMINISTRATOR = "Database Administrator"
    SYSTEM_ADMINISTRATOR = "System Administrator"
    SECURITY_ANALYST = "Security Analyst"
    INFRASTRUCTURE_ADMINISTRATOR = "Infrastructure Administrator"
    ENTERPRISE_ADMINISTRATOR = "Enterprise Administrator"


class ToolCategory(str, Enum):
    NETWORK = "network"
    DATABASE = "database"
    SERVER = "server"
    SECURITY = "security"
    LOGGING = "logging"
    KNOWLEDGE = "knowledge"


class PermissionResult(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class VerificationAction(str, Enum):
    CONTINUE = "continue"
    RETRIEVE_MORE_EVIDENCE = "retrieve_more_evidence"
    BLOCK = "block"
    ESCALATE = "escalate"


class SecuritySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DocumentCategory(str, Enum):
    SOP = "SOP"
    TOOL_DOCUMENTATION = "TOOL_DOCUMENTATION"
    INCIDENT_HISTORY = "INCIDENT_HISTORY"
    INFRASTRUCTURE_DOC = "INFRASTRUCTURE_DOC"
    TROUBLESHOOTING_GUIDE = "TROUBLESHOOTING_GUIDE"
