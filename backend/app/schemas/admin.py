from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Accounts (Users) -------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=6)
    role_name: str
    department: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role_name: str | None = None
    department: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role_name: str
    department: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- API Keys ----------------------------------------------------------------
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1)
    role_name: str
    department: str = "Automation"
    expires_in_days: int | None = None


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    role_name: str
    raw_key: str  # shown exactly once, at creation time
    key_prefix: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    role_name: str
    is_active: bool
    last_used: datetime | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Roles & Permissions ------------------------------------------------------
class RoleOut(BaseModel):
    id: str
    name: str
    description: str
    max_risk_level: str
    is_elevated: bool

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    max_risk_level: str | None = None
    description: str | None = None


class PermissionOut(BaseModel):
    id: str
    role_name: str
    category: str
    allowed: bool

    class Config:
        from_attributes = True


class PermissionUpdate(BaseModel):
    allowed: bool


# --- Execution Log -------------------------------------------------------------
class ToolExecutionOut(BaseModel):
    id: str
    execution_id: str
    request_id: str
    tool_name: str
    target: str
    status: str
    latency_ms: float
    result: dict
    source: str
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Tool Registry CRUD ---------------------------------------------------------
class ToolCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str
    category: str
    risk_level: str
    requires_approval: bool = False
    required_roles: list[str] = []
    input_schema: dict = {}
    output_schema: dict = {}
    timeout_seconds: int = 30


class ToolUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    risk_level: str | None = None
    requires_approval: bool | None = None
    required_roles: list[str] | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = None
    version: str | None = None
