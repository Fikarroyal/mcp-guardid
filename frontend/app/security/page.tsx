"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MetricCard, Panel, EmptyState } from "@/components/ui";
import { SeverityBadge, StatusPill } from "@/components/badges";
import { api } from "@/lib/api";
import type { SecurityEvent } from "@/lib/types";

export default function SecurityDashboardPage() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const data = (await api.listSecurityEvents(200)) as SecurityEvent[];
      setEvents(data);
      setLoading(false);
    })();
  }, []);

  const counts = useMemo(() => {
    const byType: Record<string, number> = {};
    let blocked = 0;
    let critical = 0;
    for (const e of events) {
      byType[e.event_type] = (byType[e.event_type] || 0) + 1;
      if (e.blocked) blocked += 1;
      if (e.severity === "CRITICAL") critical += 1;
    }
    return { byType, blocked, critical, total: events.length };
  }, [events]);

  return (
    <AppShell title="Security Overview">
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Total Security Events" value={String(counts.total)} />
        <MetricCard label="Blocked Requests" value={String(counts.blocked)} tone={counts.blocked > 0 ? "warning" : "healthy"} />
        <MetricCard label="Critical Events" value={String(counts.critical)} tone={counts.critical > 0 ? "critical" : "healthy"} />
        <MetricCard
          label="Prompt Injection Attempts"
          value={String(counts.byType["prompt_injection"] || 0)}
          tone={(counts.byType["prompt_injection"] || 0) > 0 ? "warning" : "healthy"}
        />
      </div>

      <Panel title="Recent Security Events">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : events.length === 0 ? (
          <EmptyState message="No security events recorded." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Time</th>
                <th className="font-medium pb-1.5">Event Type</th>
                <th className="font-medium pb-1.5">Severity</th>
                <th className="font-medium pb-1.5">Description</th>
                <th className="font-medium pb-1.5">Result</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className="border-b border-line last:border-0">
                  <td className="py-1.5 whitespace-nowrap text-ink-700/60">{new Date(ev.created_at).toLocaleString()}</td>
                  <td className="py-1.5 font-mono">{ev.event_type}</td>
                  <td className="py-1.5"><SeverityBadge severity={ev.severity} /></td>
                  <td className="py-1.5 text-ink-700/70 max-w-[380px] truncate" title={ev.description}>{ev.description}</td>
                  <td className="py-1.5"><StatusPill status={ev.blocked ? "BLOCKED" : "info"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>
    </AppShell>
  );
}
