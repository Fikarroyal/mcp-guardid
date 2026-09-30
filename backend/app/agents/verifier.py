"""
Independent Verifier (Section 10). Runs AFTER tool execution, checking the
plan + evidence together. This is deliberately a separate model/pass from
the Planner so a single compromised reasoning step cannot both choose a bad
action and approve its own output.
"""
from __future__ import annotations

import json

from app.agents.llm_provider import get_llm_provider
from app.security.injection_defense import scan_tool_output


async def verify(*, plan: dict, evidence: list[dict], permission_result: str) -> dict:
    provider = get_llm_provider()
    result = await provider.verify(plan=plan, evidence=evidence, permission_result=permission_result)

    # Defense-in-depth: independently re-scan every piece of evidence for
    # injection/poisoning patterns, regardless of what the LLM verifier said.
    injection_issues: list[str] = []
    for item in evidence:
        payload_text = json.dumps(item.get("result") or {}, ensure_ascii=False)
        findings = scan_tool_output(item.get("tool_name", "unknown"), payload_text)
        injection_issues.extend(f.description for f in findings)

    if injection_issues:
        result = dict(result)
        result["issues"] = list(result.get("issues", [])) + injection_issues
        result["verified"] = False
        result["required_action"] = "block"
        result["confidence"] = min(result.get("confidence", 0.5), 0.3)

    return result
