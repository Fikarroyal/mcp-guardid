"""
Static RBAC policy matrix (Section 4 of the spec).

This is intentionally NOT just a frontend concern: `PolicyEngine`
(app/security/policy_engine.py) re-checks this on every single tool
execution request, server-side, before the MCP Gateway is allowed to run
anything. Hiding a button in the UI is not authorization.
"""
from dataclasses import dataclass, field

from app.core.enums import RiskLevel, RoleName, ToolCategory


@dataclass(frozen=True)
class RolePolicy:
    role: RoleName
    allowed_categories: set[ToolCategory]
    max_risk_level: RiskLevel
    # Explicit tool-name allowlist/denylist overrides category rules when present.
    extra_allowed_tools: set[str] = field(default_factory=set)
    restricted_tools: set[str] = field(default_factory=set)
    # Whether this role counts as "elevated" for CRITICAL-tier actions.
    is_elevated: bool = False


ROLE_POLICIES: dict[RoleName, RolePolicy] = {
    RoleName.VIEWER: RolePolicy(
        role=RoleName.VIEWER,
        allowed_categories={
            ToolCategory.NETWORK,
            ToolCategory.SERVER,
            ToolCategory.DATABASE,
            ToolCategory.LOGGING,
            ToolCategory.KNOWLEDGE,
        },
        max_risk_level=RiskLevel.LOW,
    ),
    RoleName.IT_SUPPORT: RolePolicy(
        role=RoleName.IT_SUPPORT,
        allowed_categories={ToolCategory.NETWORK, ToolCategory.SERVER, ToolCategory.LOGGING, ToolCategory.KNOWLEDGE},
        max_risk_level=RiskLevel.MEDIUM,
        extra_allowed_tools={"search_logs", "query_incident_history"},
    ),
    RoleName.NETWORK_ENGINEER: RolePolicy(
        role=RoleName.NETWORK_ENGINEER,
        allowed_categories={ToolCategory.NETWORK, ToolCategory.LOGGING, ToolCategory.KNOWLEDGE},
        max_risk_level=RiskLevel.MEDIUM,
    ),
    RoleName.DATABASE_ADMINISTRATOR: RolePolicy(
        role=RoleName.DATABASE_ADMINISTRATOR,
        allowed_categories={ToolCategory.DATABASE, ToolCategory.LOGGING, ToolCategory.KNOWLEDGE},
        max_risk_level=RiskLevel.HIGH,
    ),
    RoleName.SYSTEM_ADMINISTRATOR: RolePolicy(
        role=RoleName.SYSTEM_ADMINISTRATOR,
        allowed_categories={ToolCategory.SERVER, ToolCategory.NETWORK, ToolCategory.LOGGING, ToolCategory.KNOWLEDGE},
        max_risk_level=RiskLevel.HIGH,
    ),
    RoleName.SECURITY_ANALYST: RolePolicy(
        role=RoleName.SECURITY_ANALYST,
        allowed_categories={ToolCategory.SECURITY, ToolCategory.LOGGING, ToolCategory.KNOWLEDGE},
        max_risk_level=RiskLevel.MEDIUM,
    ),
    RoleName.INFRASTRUCTURE_ADMINISTRATOR: RolePolicy(
        role=RoleName.INFRASTRUCTURE_ADMINISTRATOR,
        allowed_categories=set(ToolCategory),
        max_risk_level=RiskLevel.HIGH,
        is_elevated=True,
    ),
    RoleName.ENTERPRISE_ADMINISTRATOR: RolePolicy(
        role=RoleName.ENTERPRISE_ADMINISTRATOR,
        allowed_categories=set(ToolCategory),
        max_risk_level=RiskLevel.CRITICAL,
        is_elevated=True,
    ),
}


# Risk tiers that ALWAYS require a human approval record, independent of role,
# per Section 3: "HIGH: harus membutuhkan explicit approval."
RISK_LEVELS_REQUIRING_APPROVAL = {RiskLevel.HIGH, RiskLevel.CRITICAL}

# CRITICAL actions additionally require the requester's role to be "elevated"
# AND a second independent verification step (see VerifierService).
ONLY_ELEVATED_ROLES_MAY_REQUEST = {RiskLevel.CRITICAL}
