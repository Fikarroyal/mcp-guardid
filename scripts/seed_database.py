"""
Seeds the database with:
  - demo users (one per role) for login/testing
  - the full MCP tool catalog (mirrored from mcp_server/registry.py)
  - SOP documents (chunked) and incident history
  - the RBAC role/permission reference rows

Run:
    python -m scripts.seed_database
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.bootstrap import bootstrap_embeddings  # noqa: E402
from app.core.role_policy import ROLE_POLICIES  # noqa: E402
from app.database.session import AsyncSessionLocal, init_db  # noqa: E402
from app.models.entities import Document, DocumentChunk, Incident, McpTool, Permission, Role, User  # noqa: E402
from app.rag.chunking import chunk_document  # noqa: E402
from app.rag.seed_content import INCIDENT_HISTORY, SOP_DOCUMENTS  # noqa: E402
from app.security.auth import hash_password  # noqa: E402
from mcp_server.registry import TOOL_CATALOG  # noqa: E402

DEMO_USERS = [
    {"email": "viewer@mcpguardid.id", "full_name": "Zulfikar", "role": "Viewer", "department": "General"},
    {"email": "itsupport@mcpguardid.id", "full_name": "Rasyid", "role": "IT Support", "department": "IT Ops"},
    {"email": "netmgr@mcpguardid.id", "full_name": "Muhammad", "role": "Network Engineer", "department": "Network"},
    {"email": "dba@mcpguardid.id", "full_name": "Andy", "role": "Database Administrator", "department": "Database"},
    {"email": "sysadmin@mcpguardid.id", "full_name": "Zulkarnain", "role": "System Administrator", "department": "Infrastructure"},
    {"email": "secanalyst@mcpguardid.id", "full_name": "Zulfikar", "role": "Security Analyst", "department": "Security"},
    {"email": "infraadmin@mcpguardid.id", "full_name": "Rasyid", "role": "Infrastructure Administrator", "department": "Infrastructure"},
    {"email": "enterprise@mcpguardid.id", "full_name": "Muhammad", "role": "Enterprise Administrator", "department": "Executive"},
]
DEMO_PASSWORD = "GuardID#2026"


async def seed_roles(db) -> None:
    for role_name, policy in ROLE_POLICIES.items():
        existing = await db.execute(select(Role).where(Role.name == role_name.value))
        if existing.scalar_one_or_none():
            continue
        db.add(Role(name=role_name.value, description=f"{role_name.value} role", max_risk_level=policy.max_risk_level.value,
                     is_elevated=policy.is_elevated))
        for category in policy.allowed_categories:
            db.add(Permission(role_name=role_name.value, category=category.value, allowed=True))
    await db.flush()


async def seed_users(db) -> None:
    for u in DEMO_USERS:
        existing = await db.execute(select(User).where(User.email == u["email"]))
        row = existing.scalar_one_or_none()
        if row:
            # Idempotent re-seed: keep existing users in sync with DEMO_USERS
            # (e.g. after a display-name change) instead of silently skipping.
            row.full_name = u["full_name"]
            row.role_name = u["role"]
            row.department = u["department"]
            continue
        db.add(User(email=u["email"], full_name=u["full_name"], hashed_password=hash_password(DEMO_PASSWORD),
                     role_name=u["role"], department=u["department"]))
    await db.flush()


async def seed_tools(db) -> None:
    for tool in TOOL_CATALOG:
        existing = await db.execute(select(McpTool).where(McpTool.name == tool.name))
        if existing.scalar_one_or_none():
            continue
        db.add(McpTool(
            name=tool.name, description=tool.description, category=tool.category, risk_level=tool.risk_level,
            requires_approval=tool.requires_approval, required_roles=tool.required_roles,
            input_schema=tool.input_schema, output_schema=tool.output_schema, enabled=True, version="1.0.0",
            timeout_seconds=tool.timeout, success_rate=100.0, avg_latency_ms=0.0,
        ))
    await db.flush()


async def seed_documents(db) -> None:
    for doc in SOP_DOCUMENTS:
        existing = await db.execute(select(Document).where(Document.title == doc["title"]))
        if existing.scalar_one_or_none():
            continue
        document = Document(title=doc["title"], category=doc["category"], department=doc["department"],
                             risk_level=doc["risk_level"], content=doc["content"], version="1.0")
        db.add(document)
        await db.flush()
        for idx, chunk_text in enumerate(chunk_document(doc["content"])):
            db.add(DocumentChunk(document_id=document.id, chunk_index=idx, content=chunk_text, embedding=[]))
    await db.flush()


async def seed_incidents(db) -> None:
    for inc in INCIDENT_HISTORY:
        existing = await db.execute(select(Incident).where(Incident.code == inc["code"]))
        if existing.scalar_one_or_none():
            continue
        db.add(Incident(code=inc["code"], title=inc["title"], severity=inc["severity"], service=inc["service"],
                         status=inc["status"], root_cause=inc["root_cause"], related_tools=inc["related_tools"]))
    await db.flush()


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_roles(db)
        await seed_users(db)
        await seed_tools(db)
        await seed_documents(db)
        await seed_incidents(db)
        await db.commit()
        await bootstrap_embeddings(db)
    print("Seed complete.")
    print(f"Demo login password for all seeded users: {DEMO_PASSWORD}")
    for u in DEMO_USERS:
        print(f"  {u['email']:35s} -> {u['role']}")


if __name__ == "__main__":
    asyncio.run(main())
