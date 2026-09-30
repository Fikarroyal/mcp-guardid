"""
Tool execution backend.

`SimulatedInfrastructureAdapter` is the DEFAULT executor: this sandbox has no
real hospital network, database cluster, or servers to probe, so results are
generated deterministically (seeded by target name) so demos are reproducible,
with a few named hosts pre-scripted to reproduce the scenarios in the spec
(Section 40 / 41).

To go to production, implement `InfrastructureAdapter` with real backends:
  - network tools  -> `subprocess` ping/dig, or an SNMP/ICMP library
  - server tools    -> SSH (paramiko/fabric) or an agent (Prometheus node_exporter)
  - database tools  -> real DB drivers (psycopg2, pymysql) against a read replica
  - security tools  -> `ssl`/`cryptography` for real certificate inspection
and register it in `get_executor()`. The MCP Gateway and every layer above it
depend only on the `InfrastructureAdapter` interface, so this swap requires no
other code changes.
"""
from __future__ import annotations

import hashlib
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any


class ToolExecutionError(Exception):
    pass


class ToolTimeoutError(ToolExecutionError):
    pass


class InfrastructureAdapter(ABC):
    @abstractmethod
    def execute(self, tool_name: str, input_data: dict[str, Any]) -> dict[str, Any]: ...


def _seed_for(*parts: str) -> random.Random:
    key = "|".join(parts)
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


# Pre-scripted demo hosts so Scenario 1/2/3 in the README always reproduce the
# same evidence values described in the spec.
_SCRIPTED_TARGETS = {
    "hospital.example": {"http_response_s": 2.84, "cpu_pct": 87.0, "db_status": "healthy", "mem_pct": 71.0},
    "rs-jantung-sehat.id": {"http_response_s": 2.84, "cpu_pct": 87.0, "db_status": "healthy", "mem_pct": 71.0},
}


class SimulatedInfrastructureAdapter(InfrastructureAdapter):
    def execute(self, tool_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        method = getattr(self, f"_exec_{tool_name}", None)
        if method is None:
            raise ToolExecutionError(f"No simulated implementation for tool '{tool_name}'")
        # Simulate realistic latency per tool category.
        time.sleep(0.0)
        return method(input_data)

    # ---- network -----------------------------------------------------
    def _exec_ping_device(self, data):
        rng = _seed_for("ping", data.get("target", ""))
        return {"reachable": True, "latency_ms": round(rng.uniform(1, 40), 2), "packet_loss_pct": 0.0}

    def _exec_check_dns(self, data):
        rng = _seed_for("dns", data.get("hostname", ""))
        return {"resolved": True, "records": [f"{rng.randint(10,250)}.{rng.randint(0,255)}.0.{rng.randint(1,254)}"],
                "resolve_time_ms": round(rng.uniform(5, 60), 2)}

    def _exec_check_http(self, data):
        target = data.get("url", "")
        scripted = _SCRIPTED_TARGETS.get(target.replace("https://", "").replace("http://", "").split("/")[0])
        rng = _seed_for("http", target)
        resp_time = scripted["http_response_s"] if scripted else round(rng.uniform(0.1, 1.2), 2)
        return {"status_code": 200, "response_time_s": resp_time, "tls_valid": True}

    def _exec_check_port(self, data):
        rng = _seed_for("port", data.get("hostname", ""), str(data.get("port")))
        return {"open": rng.random() > 0.05}

    def _exec_get_network_latency(self, data):
        rng = _seed_for("latency", data.get("destination", ""))
        return {"latency_ms": round(rng.uniform(2, 55), 2)}

    # ---- server --------------------------------------------------------
    def _exec_check_server(self, data):
        rng = _seed_for("server", data.get("hostname", ""))
        return {"status": "up", "uptime_days": round(rng.uniform(10, 400), 1)}

    def _exec_check_server_status(self, data):
        return {"status": "degraded" if data.get("hostname") in _SCRIPTED_TARGETS else "healthy"}

    def _exec_check_service(self, data):
        rng = _seed_for("service", data.get("hostname", ""), data.get("service_name", ""))
        return {"running": rng.random() > 0.03}

    def _exec_get_system_metrics(self, data):
        host = data.get("hostname", "")
        scripted = _SCRIPTED_TARGETS.get(host)
        rng = _seed_for("sysmetrics", host)
        return {
            "cpu_usage_pct": scripted["cpu_pct"] if scripted else round(rng.uniform(10, 60), 1),
            "memory_usage_pct": scripted["mem_pct"] if scripted else round(rng.uniform(20, 70), 1),
            "disk_usage_pct": round(rng.uniform(30, 80), 1),
        }

    def _exec_get_cpu_usage(self, data):
        host = data.get("hostname", "")
        scripted = _SCRIPTED_TARGETS.get(host)
        rng = _seed_for("cpu", host)
        return {"cpu_usage_pct": scripted["cpu_pct"] if scripted else round(rng.uniform(10, 60), 1)}

    def _exec_get_memory_usage(self, data):
        host = data.get("hostname", "")
        scripted = _SCRIPTED_TARGETS.get(host)
        rng = _seed_for("mem", host)
        return {"memory_usage_pct": scripted["mem_pct"] if scripted else round(rng.uniform(20, 70), 1)}

    def _exec_get_disk_usage(self, data):
        rng = _seed_for("disk", data.get("hostname", ""))
        return {"disk_usage_pct": round(rng.uniform(30, 85), 1)}

    def _exec_get_process_status(self, data):
        rng = _seed_for("proc", data.get("hostname", ""), data.get("process_name", ""))
        return {"running": rng.random() > 0.05, "memory_mb": round(rng.uniform(50, 900), 1)}

    # ---- database --------------------------------------------------------
    def _exec_check_database(self, data):
        db = data.get("database_name", "")
        scripted = _SCRIPTED_TARGETS.get(db) or next(iter(_SCRIPTED_TARGETS.values()), None)
        rng = _seed_for("db", db)
        return {"status": "healthy", "connections": rng.randint(5, 120)}

    def _exec_query_database_readonly(self, data):
        rng = _seed_for("dbquery", data.get("database_name", ""), data.get("query_id", ""))
        return {"rows": [{"metric": "row_count", "value": rng.randint(100, 100000)}]}

    def _exec_get_database_metrics(self, data):
        rng = _seed_for("dbmetrics", data.get("database_name", ""))
        return {
            "connection_pool_usage_pct": round(rng.uniform(20, 90), 1),
            "avg_query_latency_ms": round(rng.uniform(2, 80), 1),
            "replication_lag_s": round(rng.uniform(0, 3), 2),
        }

    # ---- logging / knowledge --------------------------------------------
    def _exec_search_logs(self, data):
        rng = _seed_for("logs", data.get("service", ""), data.get("query", ""))
        n = rng.randint(0, 6)
        now = datetime.utcnow()
        return {"matches": [
            {"timestamp": (now - timedelta(minutes=rng.randint(1, 120))).isoformat(),
             "level": rng.choice(["WARN", "ERROR", "INFO"]),
             "message": f"{data.get('service','service')} log entry #{i+1} matching '{data.get('query','')}'"}
            for i in range(n)
        ]}

    def _exec_query_incident_history(self, data):
        # Delegated to the RAG incident index by the backend service layer;
        # the standalone MCP server returns a lightweight stub for direct calls.
        return {"incidents": []}

    def _exec_search_sop(self, data):
        return {"documents": []}

    # ---- security ----------------------------------------------------
    def _exec_check_ssl(self, data):
        rng = _seed_for("ssl", data.get("hostname", ""))
        days = rng.randint(-5, 200)
        return {"valid": days > 0, "days_until_expiry": days, "issuer": "DigiCert Inc"}

    def _exec_check_certificate(self, data):
        rng = _seed_for("cert", data.get("hostname", ""))
        return {"trusted": rng.random() > 0.1}

    # ---- HIGH risk (approval-gated; only reached after approval) --------
    def _exec_restart_service(self, data):
        return {"restarted": True, "service_name": data.get("service_name")}

    def _exec_restart_database(self, data):
        return {"restarted": True, "database_name": data.get("database_name")}

    def _exec_clear_cache(self, data):
        return {"cleared": True, "target": data.get("target")}

    def _exec_modify_configuration(self, data):
        return {"applied": True, "target": data.get("target")}

    # ---- CRITICAL risk (approval + elevated role + extra verification) --
    def _exec_delete_database(self, data):
        return {"deleted": True, "database_name": data.get("database_name")}

    def _exec_shutdown_server(self, data):
        return {"shutdown": True, "hostname": data.get("hostname")}

    def _exec_modify_firewall(self, data):
        return {"applied": True, "rule": data.get("rule")}

    def _exec_delete_production_data(self, data):
        return {"deleted": True, "target": data.get("target")}


_adapter_instance: InfrastructureAdapter | None = None


def get_executor() -> InfrastructureAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = SimulatedInfrastructureAdapter()
    return _adapter_instance
