import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.entity_extraction import build_tool_input, extract_target
from app.agents.intent import classify_intent
from app.api.deps import get_current_user, require_roles
from app.core.bootstrap import bootstrap_embeddings
from app.core.enums import RiskLevel, ToolCategory
from app.rag.vector_store import get_vector_store
from app.schemas.admin import ToolCreate, ToolUpdate
from app.database.session import get_db
from app.mcp import gateway
from app.models.entities import McpTool, User
from app.routing.tool_retrieval import retrieve_tools
from app.schemas.tools import ToolCandidate, ToolExecuteRequest, ToolOut, ToolSearchRequest, ToolSearchResponse

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
async def list_tools(db: AsyncSession = Depends(get_db)) -> list[McpTool]:
    result = await db.execute(select(McpTool).order_by(McpTool.category, McpTool.name))
    return list(result.scalars().all())


@router.get("/{tool_id}", response_model=ToolOut)
async def get_tool(tool_id: str, db: AsyncSession = Depends(get_db)) -> McpTool:
    tool = await db.get(McpTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    return tool


@router.post("/search", response_model=ToolSearchResponse)
async def search_tools(
    payload: ToolSearchRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ToolSearchResponse:
    intent_result = classify_intent(payload.query)
    candidates = await retrieve_tools(
        db, query=payload.query, role_name=current_user.role_name, intent_result=intent_result, top_k=payload.top_k,
    )
    return ToolSearchResponse(
        query=payload.query, detected_intent=intent_result.intent,
        candidates=[ToolCandidate(name=c.tool_name, category="", risk_level="", semantic_score=c.semantic_score,
                                   intent_score=c.intent_score, permission_score=c.permission_score,
                                   context_score=c.context_score, historical_success=c.historical_success,
                                   risk_score=c.risk_score, final_score=c.final_score,
                                   permission_result=c.permission_result)
                    for c in candidates],
    )


@router.post("/{tool_id}/execute")
async def execute_tool_directly(
    tool_id: str, payload: ToolExecuteRequest, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tool = await db.get(McpTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")

    request_id = str(uuid.uuid4())
    target_ctx = extract_target(payload.target or tool.name)
    input_data = payload.input_data or build_tool_input(tool.name, tool.input_schema, target_ctx, payload.reason)

    try:
        evidence = await gateway.execute_tool(
            db, tool=tool, role_name=current_user.role_name, input_data=input_data,
            target=payload.target or target_ctx.get("hostname", ""), request_id=request_id, approval_confirmed=False,
        )
        await db.commit()
        return {"status": "executed", "evidence": evidence}
    except gateway.ApprovalRequiredError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail=f"Approval required: {exc}. Submit via POST /api/v1/approvals first.") from exc
    except gateway.PermissionDeniedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except gateway.InputValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


# --------------------------------------------------------------- Registry CRUD --
_TOOL_ADMINS = ("Infrastructure Administrator", "Enterprise Administrator")


def _validate_risk_and_category(risk_level: str | None, category: str | None) -> None:
    try:
        if risk_level is not None:
            RiskLevel(risk_level)
        if category is not None:
            ToolCategory(category)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid value: {exc}") from exc


@router.post("", response_model=ToolOut, status_code=status.HTTP_201_CREATED)
async def create_tool(
    payload: ToolCreate, current_user: User = Depends(require_roles(*_TOOL_ADMINS)), db: AsyncSession = Depends(get_db),
) -> McpTool:
    _validate_risk_and_category(payload.risk_level, payload.category)
    existing = await db.execute(select(McpTool).where(McpTool.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A tool with this name already exists.")
    risk = RiskLevel(payload.risk_level)
    tool = McpTool(
        name=payload.name, description=payload.description, category=payload.category, risk_level=payload.risk_level,
        # HIGH/CRITICAL tools ALWAYS require approval -- not caller-controllable.
        requires_approval=payload.requires_approval or risk.rank >= RiskLevel.HIGH.rank,
        required_roles=payload.required_roles, input_schema=payload.input_schema, output_schema=payload.output_schema,
        timeout_seconds=payload.timeout_seconds, enabled=True, version="1.0.0",
    )
    db.add(tool)
    await db.commit()
    await bootstrap_embeddings(db)  # make the new tool discoverable by semantic retrieval
    await db.refresh(tool)
    return tool


@router.put("/{tool_id}", response_model=ToolOut)
async def update_tool(
    tool_id: str, payload: ToolUpdate, current_user: User = Depends(require_roles(*_TOOL_ADMINS)),
    db: AsyncSession = Depends(get_db),
) -> McpTool:
    tool = await db.get(McpTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    _validate_risk_and_category(payload.risk_level, payload.category)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tool, field, value)
    if RiskLevel(tool.risk_level).rank >= RiskLevel.HIGH.rank:
        tool.requires_approval = True
    await db.commit()
    await bootstrap_embeddings(db)  # keep the vector index in sync with edited descriptions/flags
    await db.refresh(tool)
    return tool


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str, current_user: User = Depends(require_roles(*_TOOL_ADMINS)), db: AsyncSession = Depends(get_db),
) -> dict:
    tool = await db.get(McpTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    name = tool.name
    await db.delete(tool)
    await db.commit()
    get_vector_store().delete("mcp_tools", name)
    return {"status": "deleted", "tool": name}
