"""
Context & Role Analysis stage: pulls a concrete target (hostname/database
name/service) out of the free-text query so tool inputs can be constructed,
and maps that target onto each candidate tool's declared input_schema.

This is intentionally simple (keyword heuristics) -- in production this
stage would resolve against a CMDB / service catalog instead of guessing.
"""
from __future__ import annotations

_HOSPITAL_KEYWORDS = ("rumah sakit", "hospital", "rs ", "klinik")
_DATABASE_KEYWORDS = ("database", "db ", " db")


def extract_target(query: str) -> dict[str, str]:
    lowered = query.lower()
    if any(k in lowered for k in _HOSPITAL_KEYWORDS):
        return {"hostname": "hospital.example", "database_name": "hospital-patient-db",
                "service": "hospital-website", "url": "https://hospital.example"}
    if any(k in lowered for k in _DATABASE_KEYWORDS):
        return {"hostname": "db-primary-01.internal", "database_name": "core-database",
                "service": "core-database", "url": "https://portal.internal"}
    return {"hostname": "server-01.internal", "database_name": "core-database",
            "service": "app-service", "url": "https://portal.internal"}


def build_tool_input(tool_name: str, input_schema: dict, target_ctx: dict[str, str], query: str) -> dict:
    required = (input_schema or {}).get("required", [])
    properties = (input_schema or {}).get("properties", {})
    data: dict = {}
    for field in required:
        if field in ("hostname", "target", "destination"):
            data[field] = target_ctx["hostname"]
        elif field == "url":
            data[field] = target_ctx["url"]
        elif field == "database_name":
            data[field] = target_ctx["database_name"]
        elif field == "service":
            data[field] = target_ctx["service"]
        elif field == "service_name":
            data[field] = "web-frontend"
        elif field == "process_name":
            data[field] = "app-process"
        elif field == "port":
            data[field] = 443
        elif field == "query":
            data[field] = query
        elif field == "query_id":
            data[field] = "diag-001"
        elif field == "rule":
            data[field] = "requested-rule-change"
        elif field == "change":
            data[field] = "requested configuration change"
        elif field in properties:
            data[field] = target_ctx.get(field, "unspecified")
    return data
