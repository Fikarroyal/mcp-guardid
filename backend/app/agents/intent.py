"""
Intent understanding (first stage of the pipeline: User Request -> Intent
Understanding). Two layers, in order:

1. Deterministic keyword rules for safety-critical intents (restart, delete,
   shutdown, firewall changes...). These MUST be caught reliably regardless
   of embedding noise -- a misclassified "restart_database" as a harmless
   diagnostic intent would be a serious safety bug, so it is not left to a
   similarity score alone.
2. Embedding-based nearest-centroid match against example utterances for the
   remaining diagnostic/informational intents.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.enums import RiskLevel

# intent_name -> (example utterances used to fit its centroid, canonical tool set, nominal risk)
INTENT_DEFINITIONS: dict[str, dict] = {
    "website_performance": {
        "examples": [
            "website lambat", "website rumah sakit lambat", "situs down", "web tidak bisa diakses",
            "website slow", "site is down", "cek kenapa website lambat", "http timeout",
        ],
        "tools": ["check_http", "check_server", "get_cpu_usage", "get_memory_usage", "check_dns", "search_logs"],
        "risk": RiskLevel.LOW,
    },
    "database_health": {
        "examples": [
            "cek status database", "database timeout", "db connection error", "check database health",
            "database lambat", "koneksi database gagal", "cek kesehatan database",
        ],
        "tools": ["check_database", "get_database_metrics", "query_database_readonly", "search_logs"],
        "risk": RiskLevel.LOW,
    },
    "dns_issue": {
        "examples": ["dns tidak resolve", "dns resolution failure", "hostname tidak ditemukan", "gagal resolve domain"],
        "tools": ["check_dns", "ping_device"],
        "risk": RiskLevel.LOW,
    },
    "network_latency": {
        "examples": ["latency tinggi", "koneksi lambat", "network congestion", "ping tinggi", "packet loss"],
        "tools": ["get_network_latency", "ping_device", "check_port"],
        "risk": RiskLevel.LOW,
    },
    "ssl_certificate": {
        "examples": ["sertifikat ssl", "ssl warning", "certificate expired", "https tidak aman", "cek sertifikat"],
        "tools": ["check_ssl", "check_certificate"],
        "risk": RiskLevel.LOW,
    },
    "incident_lookup": {
        "examples": ["cari incident serupa", "riwayat insiden", "pernah terjadi sebelumnya", "incident history"],
        "tools": ["query_incident_history", "search_sop"],
        "risk": RiskLevel.MEDIUM,
    },
    "sop_lookup": {
        "examples": ["sop untuk restart database", "prosedur maintenance server", "dokumentasi troubleshooting"],
        "tools": ["search_sop"],
        "risk": RiskLevel.LOW,
    },
    "general_diagnostics": {
        "examples": ["cek kondisi server", "system health check", "cek status infrastruktur", "server metrics"],
        "tools": ["check_server_status", "get_system_metrics", "get_process_status"],
        "risk": RiskLevel.LOW,
    },
}

# (regex, intent_name, primary_tool, risk) -- checked BEFORE the embedding fallback.
_HIGH_SIGNAL_RULES: list[tuple[str, str, str, RiskLevel]] = [
    (r"restart\s+(the\s+)?database|restart\s+database", "restart_database", "restart_database", RiskLevel.HIGH),
    (r"restart\s+(the\s+)?service|restart\s+service", "restart_service", "restart_service", RiskLevel.HIGH),
    (r"clear\s+(the\s+)?cache|clear\s+cache|hapus\s+cache", "clear_cache", "clear_cache", RiskLevel.HIGH),
    (r"(modify|change|update)\s+(the\s+)?config", "modify_configuration", "modify_configuration", RiskLevel.HIGH),
    (r"delete\s+(the\s+)?database|hapus\s+database|drop\s+database", "delete_database", "delete_database", RiskLevel.CRITICAL),
    (r"shut ?down\s+(the\s+)?server|matikan\s+server", "shutdown_server", "shutdown_server", RiskLevel.CRITICAL),
    (r"(modify|change|update)\s+(the\s+)?firewall|ubah\s+firewall", "modify_firewall", "modify_firewall", RiskLevel.CRITICAL),
    (r"delete\s+(production\s+)?data|hapus\s+data\s+produksi", "delete_production_data", "delete_production_data", RiskLevel.CRITICAL),
]


@dataclass
class IntentResult:
    intent: str
    canonical_tools: list[str]
    nominal_risk: RiskLevel
    method: str  # "rule" | "embedding"
    forced_tool: str | None = None


def classify_intent(query: str) -> IntentResult:
    lowered = query.lower()
    for pattern, intent_name, tool, risk in _HIGH_SIGNAL_RULES:
        if re.search(pattern, lowered):
            return IntentResult(intent=intent_name, canonical_tools=[tool], nominal_risk=risk,
                                 method="rule", forced_tool=tool)

    # Embedding fallback: compare against each intent's centroid.
    from app.rag.embeddings import cosine_similarity, get_embedding_provider

    provider = get_embedding_provider()
    query_vec = provider.embed(query)
    best_intent, best_score = "general_diagnostics", -1.0
    for name, definition in INTENT_DEFINITIONS.items():
        centroid = _centroid_cache().get(name)
        if centroid is None:
            continue
        score = cosine_similarity(query_vec, centroid)
        if score > best_score:
            best_intent, best_score = name, score

    definition = INTENT_DEFINITIONS[best_intent]
    return IntentResult(intent=best_intent, canonical_tools=definition["tools"], nominal_risk=definition["risk"],
                         method="embedding")


_CENTROIDS: dict[str, list[float]] | None = None


def build_intent_centroids() -> None:
    """Called once at startup, after the embedding provider has been fit on
    the full corpus, to precompute a centroid vector per intent."""
    import numpy as np

    from app.rag.embeddings import get_embedding_provider

    global _CENTROIDS
    provider = get_embedding_provider()
    centroids: dict[str, list[float]] = {}
    for name, definition in INTENT_DEFINITIONS.items():
        vecs = [provider.embed(ex) for ex in definition["examples"]]
        centroids[name] = np.mean(np.array(vecs), axis=0).tolist()
    _CENTROIDS = centroids


def _centroid_cache() -> dict[str, list[float]]:
    if _CENTROIDS is None:
        build_intent_centroids()
    return _CENTROIDS  # type: ignore[return-value]


def all_example_utterances() -> list[str]:
    out = []
    for definition in INTENT_DEFINITIONS.values():
        out.extend(definition["examples"])
    return out
