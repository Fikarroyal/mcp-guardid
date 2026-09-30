"""
Policy Engine -- the single, server-side source of truth for authorization.

This is deliberately re-invoked on every tool-execution path (never trusted
from the frontend). Given a user's role and a target tool, it returns one of:

    ALLOWED            -> the MCP Gateway may execute immediately
    DENIED              -> role can never run this tool/category/risk tier
    APPROVAL_REQUIRED   -> execution is held until an Approval record with
                           status=APPROVED exists for this exact request_id
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import PermissionResult, RiskLevel, RoleName
from app.security import policy_overrides
from app.core.role_policy import (
    ONLY_ELEVATED_ROLES_MAY_REQUEST,
    RISK_LEVELS_REQUIRING_APPROVAL,
    ROLE_POLICIES,
)


@dataclass
class PolicyDecision:
    result: PermissionResult
    reason: str
    required_role: str | None = None


class PolicyEngine:
    def evaluate(
        self,
        *,
        role_name: str,
        tool_name: str,
        tool_category: str,
        tool_risk_level: str,
        tool_required_roles: list[str],
    ) -> PolicyDecision:
        try:
            role = RoleName(role_name)
        except ValueError:
            return PolicyDecision(PermissionResult.DENIED, f"Unknown role '{role_name}'.")

        policy = ROLE_POLICIES.get(role)
        if policy is None:
            return PolicyDecision(PermissionResult.DENIED, f"No policy configured for role '{role_name}'.")

        risk = RiskLevel(tool_risk_level)

        # 1. Explicit tool-level required_roles always wins if it's more specific.
        if tool_required_roles and role.value not in tool_required_roles:
            return PolicyDecision(
                PermissionResult.DENIED,
                f"Tool '{tool_name}' requires one of roles {tool_required_roles}; user has '{role.value}'.",
                required_role=tool_required_roles[0],
            )

        # 1b. Admin-configured category block (Roles & Permissions page).
        if (role.value, tool_category) in policy_overrides.blocked_categories:
            return PolicyDecision(
                PermissionResult.DENIED,
                f"Role '{role.value}' has been blocked from category '{tool_category}' by an administrator.",
            )

        # 2. Category gate -- ONLY applies as a fallback for tools that do not
        # declare their own `required_roles` (step 1 already validated against
        # that authoritative, per-tool list; re-checking a coarser
        # role->category matrix on top of it would contradict a tool that
        # deliberately grants a broader set of roles, e.g. a read-only health
        # check open to IT Support even though category="database").
        if not tool_required_roles:
            try:
                from app.core.enums import ToolCategory

                category = ToolCategory(tool_category)
                if category not in policy.allowed_categories and tool_name not in policy.extra_allowed_tools:
                    return PolicyDecision(
                        PermissionResult.DENIED,
                        f"Role '{role.value}' is not authorized for category '{tool_category}'.",
                    )
            except ValueError:
                pass  # unknown category -> fall through to risk gate only

        # 3. Explicit restriction.
        if tool_name in policy.restricted_tools:
            return PolicyDecision(PermissionResult.DENIED, f"Tool '{tool_name}' is explicitly restricted for this role.")

        # 4. Risk ceiling for the role.
        ceiling = RiskLevel(policy_overrides.max_risk.get(role.value, policy.max_risk_level.value))
        if risk.rank > ceiling.rank:
            return PolicyDecision(
                PermissionResult.DENIED,
                f"Role '{role.value}' max risk level is {ceiling.value}; "
                f"tool risk is {risk.value}.",
            )

        # 5. CRITICAL actions require an elevated role even if risk ceiling technically allows it.
        if risk in ONLY_ELEVATED_ROLES_MAY_REQUEST and not policy.is_elevated:
            return PolicyDecision(
                PermissionResult.DENIED,
                f"CRITICAL actions require an elevated role (Enterprise Administrator).",
            )

        # 6. Risk tiers that always require human approval, regardless of role.
        if risk in RISK_LEVELS_REQUIRING_APPROVAL:
            return PolicyDecision(
                PermissionResult.APPROVAL_REQUIRED,
                f"{risk.value} risk actions require explicit human approval before execution.",
                required_role=tool_required_roles[0] if tool_required_roles else None,
            )

        return PolicyDecision(PermissionResult.ALLOWED, "Permission granted: risk within role ceiling, no approval tier.")


_engine = PolicyEngine()


def get_policy_engine() -> PolicyEngine:
    return _engine
