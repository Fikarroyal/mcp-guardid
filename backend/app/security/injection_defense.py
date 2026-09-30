"""
Prompt-injection & tool-poisoning defense (Section 11 / 20 of the spec).

Core principle enforced throughout the codebase: tool output, retrieved
documents, and SOPs are DATA. They are wrapped and passed to the LLM inside
clearly delimited, explicitly-labeled blocks (see
`app/agents/prompt_builder.py`) and are NEVER concatenated into the system
instructions. This module is the pattern-matching layer that flags
suspicious content for the Verifier and the Security Dashboard; it is one
layer of defense-in-depth, not the only one -- the Policy Engine's
server-side RBAC/risk checks are what actually stop unauthorized execution
even if a pattern here is missed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.enums import SecuritySeverity


@dataclass
class SecurityFinding:
    finding_type: str
    severity: SecuritySeverity
    matched_text: str
    description: str


# Each pattern is intentionally broad (case-insensitive substrings / regex)
# because attackers vary phrasing; false positives are cheap (they get
# reviewed by the Verifier / a human), false negatives are not.
_POLICY_OVERRIDE_PATTERNS = [
    r"ignore (all|the|previous|prior)\s+(security\s+)?(rules?|polic(y|ies)|instructions?)",
    r"disregard (the|all)\s+(security\s+)?(rules?|polic(y|ies)|instructions?)",
    r"forget (your|all|previous)\s+(instructions?|rules?)",
    r"bypass\s+(the\s+)?(approval|security|policy|rbac)",
    r"you are now\s+(in\s+)?(admin|root|developer|unrestricted)\s*mode",
    r"act as\s+(if\s+you\s+(are|were)\s+)?(an?\s+)?(admin|root|system)",
    r"new system prompt",
    r"override\s+(the\s+)?(previous|system)\s+instructions?",
]

_ROLE_MANIPULATION_PATTERNS = [
    r"i am (the\s+)?(administrator|admin|infrastructure administrator|enterprise administrator|root)\b",
    r"i have (admin|administrator|root|elevated)\s+(access|privileges?|rights?)",
    r"trust me,?\s+i('m| am)\s+authorized",
    r"my role is (enterprise administrator|infrastructure administrator)",
]

_FAKE_APPROVAL_PATTERNS = [
    r"(system|admin|manager|supervisor)\s+(already\s+)?approved\s+(this|the)\s+(action|request)",
    r"approval (was|has been|is)\s+(already\s+)?(granted|given|confirmed)",
    r"this (action|request) (was|is)\s+pre[- ]?approved",
    r"no need for approval",
]

_DESTRUCTIVE_INTENT_PATTERNS = [
    r"delete\s+(the\s+)?(production|prod)\s+(database|data)",
    r"shut ?down\s+(the\s+)?(production\s+)?server",
    r"wipe\s+(the\s+)?(database|disk|server)",
    r"drop\s+(table|database)",
]

_TOOL_OUTPUT_INJECTION_PATTERNS = [
    r"ignore (previous|all)\s+instructions?\s+and\s+(delete|restart|shutdown|drop|modify)",
    r"execute\s+the\s+following\s+command",
    r"as\s+the\s+(ai|assistant|model),?\s+you\s+(must|should)\s+now",
    r"<\s*system\s*>",
]

_INDIRECT_INJECTION_PATTERNS = _POLICY_OVERRIDE_PATTERNS + _TOOL_OUTPUT_INJECTION_PATTERNS


def _scan(text: str, patterns: list[str], finding_type: str, severity: SecuritySeverity, description: str) -> list[SecurityFinding]:
    findings = []
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            findings.append(SecurityFinding(
                finding_type=finding_type,
                severity=severity,
                matched_text=match.group(0),
                description=description,
            ))
    return findings


def scan_user_input(text: str) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    findings += _scan(text, _POLICY_OVERRIDE_PATTERNS, "prompt_injection", SecuritySeverity.HIGH,
                       "User message attempts to override system/security instructions.")
    findings += _scan(text, _ROLE_MANIPULATION_PATTERNS, "role_manipulation", SecuritySeverity.HIGH,
                       "User message claims an elevated role/identity to bypass authorization.")
    findings += _scan(text, _FAKE_APPROVAL_PATTERNS, "fake_approval", SecuritySeverity.HIGH,
                       "User message asserts an approval that is not backed by an Approval record.")
    findings += _scan(text, _DESTRUCTIVE_INTENT_PATTERNS, "destructive_action_without_approval", SecuritySeverity.MEDIUM,
                       "User message requests a destructive action; must route through risk/approval gate.")
    return findings


def scan_tool_output(tool_name: str, output_text: str) -> list[SecurityFinding]:
    findings = _scan(output_text, _TOOL_OUTPUT_INJECTION_PATTERNS, "malicious_tool_output", SecuritySeverity.CRITICAL,
                      f"Output of tool '{tool_name}' contains embedded instruction-like text; treated as inert data.")
    return findings


def scan_document(content: str, source_label: str = "document") -> list[SecurityFinding]:
    findings = _scan(content, _INDIRECT_INJECTION_PATTERNS, "indirect_prompt_injection", SecuritySeverity.HIGH,
                      f"Retrieved {source_label} contains embedded instruction-like text; treated as inert context.")
    return findings


def is_blocked(findings: list[SecurityFinding]) -> bool:
    return any(f.severity in (SecuritySeverity.HIGH, SecuritySeverity.CRITICAL) for f in findings)
