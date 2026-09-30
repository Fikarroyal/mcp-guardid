"""
Runtime overrides for the RBAC matrix, editable from the Roles & Permissions
page and persisted in the `roles` / `permissions` tables.

`ROLE_POLICIES` (app/core/role_policy.py) stays the built-in default. This
module layers two admin-editable adjustments on top, and `PolicyEngine`
consults them on every evaluation, so editing them in the UI genuinely
changes authorization behavior (it is not decorative):

  - max_risk[role]      -> replaces that role's risk ceiling
  - blocked_categories  -> (role, category) pairs an admin has switched OFF;
                           every tool in that category is DENIED for that
                           role, even if the tool's own `required_roles`
                           would otherwise have allowed it.

Safety rails that overrides can NOT weaken (enforced in PolicyEngine, not
here): HIGH/CRITICAL always need an Approval record; CRITICAL always needs
an elevated role.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Permission, Role

max_risk: dict[str, str] = {}
blocked_categories: set[tuple[str, str]] = set()


async def reload_overrides(db: AsyncSession) -> None:
    roles = (await db.execute(select(Role))).scalars().all()
    perms = (await db.execute(select(Permission))).scalars().all()
    max_risk.clear()
    max_risk.update({r.name: r.max_risk_level for r in roles})
    blocked_categories.clear()
    blocked_categories.update({(p.role_name, p.category) for p in perms if not p.allowed})
