"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Database, ShieldAlert, Timer } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MetricCard, Panel, EmptyState } from "@/components/ui";
import { PermissionBadge, RiskBadge, SeverityBadge, StatusPill } from "@/components/badges";
import { api } from "@/lib/api";
import type { AuditLog, Incident, SecurityEvent, SystemHealth } from "@/lib/types";

export default function OverviewPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [h, inc, audit, sec] = await Promise.all([
          api.systemHealth(),
          api.listIncidents(),
          api.listAudit({ limit: 8 }),
          api.listSecurityEvents(6),
        ]);
        setHealth(h as SystemHealth);
        setIncidents((inc as Incident[]).filter((i) => i.status !== "RESOLVED").slice(0, 5));
        setLogs(audit as AuditLog[]);
        setEvents(sec as SecurityEvent[]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const activeCount = incidents.length;
  const blockedCount = logs.filter((l) => l.status === "BLOCKED").length;
  const pendingCount = logs.filter((l) => l.status === "PENDING_APPROVAL").length;

  return (
    <AppShell title="Overview">
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Active Incidents" value={String(activeCount)} icon={AlertTriangle} tone={activeCount > 0 ? "warning" : "healthy"} />
        <MetricCard label="Requests Blocked (recent)" value={String(blockedCount)} icon={ShieldAlert} tone={blockedCount > 0 ? "critical" : "healthy"} />
        <MetricCard label="Pending Approvals" value={String(pendingCount)} icon={Timer} tone={pendingCount > 0 ? "warning" : "healthy"} />
        <MetricCard label="MCP Tools Registered" value="29" icon={Database} sublabel="across 6 categories" />
      </div>

      <div className="grid grid-cols-6 gap-3 mb-5">
        {health &&
          (
            [
              ["API", health.api],
              ["MCP Gateway", health.mcp_gateway],
              ["Database", health.database],
              ["Vector Store", health.vector_store],
              ["LLM Service", health.llm_service],
              ["Redis", health.redis],
            ] as [string, string][]
          ).map(([label, status]) => (
            <div key={label} className="border border-line bg-white rounded-sm px-3 py-2.5 flex flex-col gap-1.5">
              <span className="text-[10.5px] text-ink-700/55 font-medium">{label}</span>
              <StatusPill status={status} />
            </div>
          ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2 space-y-3">
          <Panel title="Tool Routing Activity">
            {loading ? (
              <EmptyState message="Loading…" />
            ) : logs.length === 0 ? (
              <EmptyState message="No requests recorded yet." />
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-xs">
                <thead>
                  <tr className="text-left text-ink-700/50 border-b border-line">
                    <th className="font-medium pb-1.5">Query</th>
                    <th className="font-medium pb-1.5">Intent</th>
                    <th className="font-medium pb-1.5">Risk</th>
                    <th className="font-medium pb-1.5">Permission</th>
                    <th className="font-medium pb-1.5">Status</th>
                    <th className="font-medium pb-1.5 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-line last:border-0 row-in">
                      <td className="py-1.5 pr-2 max-w-[220px] truncate" title={log.user_query}>{log.user_query}</td>
                      <td className="py-1.5 pr-2 text-ink-700/70">{log.detected_intent}</td>
                      <td className="py-1.5 pr-2"><RiskBadge risk={log.risk_level} /></td>
                      <td className="py-1.5 pr-2"><PermissionBadge permission={log.permission_result} /></td>
                      <td className="py-1.5 pr-2"><StatusPill status={log.status} /></td>
                      <td className="py-1.5 text-right tabular text-ink-700/70">{log.execution_latency_ms.toFixed(0)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-3">
          <Panel title="Active Incidents">
            {incidents.length === 0 ? (
              <EmptyState message="No active incidents." />
            ) : (
              <ul className="space-y-2">
                {incidents.map((inc) => (
                  <li key={inc.id} className="flex items-start justify-between gap-2 text-xs">
                    <div>
                      <div className="font-medium text-ink-950">{inc.code}</div>
                      <div className="text-ink-700/60">{inc.title}</div>
                    </div>
                    <SeverityBadge severity={inc.severity} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Security Events">
            {events.length === 0 ? (
              <EmptyState message="No security events." />
            ) : (
              <ul className="space-y-2">
                {events.map((ev) => (
                  <li key={ev.id} className="flex items-start justify-between gap-2 text-xs">
                    <div>
                      <div className="font-medium text-ink-950">{ev.event_type.replace(/_/g, " ")}</div>
                      <div className="text-ink-700/50 text-[10.5px]">{new Date(ev.created_at).toLocaleTimeString()}</div>
                    </div>
                    <StatusPill status={ev.blocked ? "BLOCKED" : "info"} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
