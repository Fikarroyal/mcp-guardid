import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root (for mcp_server)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mcp_guardid.db")
os.environ.setdefault("JWT_SECRET", "test-secret-key")

import pytest_asyncio  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.bootstrap import bootstrap_embeddings  # noqa: E402
from app.database.session import AsyncSessionLocal, engine, init_db  # noqa: E402
from app.models.entities import User  # noqa: E402
from app.rag.chunking import chunk_document  # noqa: E402
from app.rag.seed_content import INCIDENT_HISTORY, SOP_DOCUMENTS  # noqa: E402
from app.core.role_policy import ROLE_POLICIES  # noqa: E402
from app.security.auth import hash_password  # noqa: E402
from app.security.policy_overrides import reload_overrides  # noqa: E402
from mcp_server.registry import TOOL_CATALOG  # noqa: E402

TEST_DB_PATH = Path(__file__).resolve().parents[1] / "test_mcp_guardid.db"

ROLE_EMAILS = {
    "Viewer": "viewer@mcpguardid.id",
    "IT Support": "itsupport@mcpguardid.id",
    "Database Administrator": "dba@mcpguardid.id",
    "Infrastructure Administrator": "infraadmin@mcpguardid.id",
    "Enterprise Administrator": "enterprise@mcpguardid.id",
}
TEST_PASSWORD = "TestPass#123"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _seeded_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    await init_db()
    async with AsyncSessionLocal() as db:
        from app.models.entities import Document, DocumentChunk, Incident, McpTool, Role

        for role_name, policy in ROLE_POLICIES.items():
            db.add(Role(name=role_name.value, description=role_name.value, max_risk_level=policy.max_risk_level.value,
                        is_elevated=policy.is_elevated))

        for tool in TOOL_CATALOG:
            db.add(McpTool(
                name=tool.name, description=tool.description, category=tool.category, risk_level=tool.risk_level,
                requires_approval=tool.requires_approval, required_roles=tool.required_roles,
                input_schema=tool.input_schema, output_schema=tool.output_schema, enabled=True,
                timeout_seconds=tool.timeout,
            ))
        for email, role in [(v, k) for k, v in ROLE_EMAILS.items()]:
            db.add(User(email=email, full_name=role, hashed_password=hash_password(TEST_PASSWORD), role_name=role))
        for doc in SOP_DOCUMENTS:
            document = Document(title=doc["title"], category=doc["category"], department=doc["department"],
                                 risk_level=doc["risk_level"], content=doc["content"], version="1.0")
            db.add(document)
            await db.flush()
            for idx, chunk_text in enumerate(chunk_document(doc["content"])):
                db.add(DocumentChunk(document_id=document.id, chunk_index=idx, content=chunk_text, embedding=[]))
        for inc in INCIDENT_HISTORY:
            db.add(Incident(code=inc["code"], title=inc["title"], severity=inc["severity"], service=inc["service"],
                             status=inc["status"], root_cause=inc["root_cause"], related_tools=inc["related_tools"]))
        await db.commit()
        await bootstrap_embeddings(db)
        await reload_overrides(db)

    yield
    await engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


async def get_user(db_session, role_name: str) -> User:
    result = await db_session.execute(select(User).where(User.email == ROLE_EMAILS[role_name]))
    return result.scalar_one()
