"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState } from "@/components/ui";
import { SeverityBadge, StatusPill } from "@/components/badges";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/types";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Incident | null>(null);

  useEffect(() => {
    (async () => {
      const data = (await api.listIncidents()) as Incident[];
      setIncidents(data);
      setLoading(false);
    })();
  }, []);

  return (
    <AppShell title="Incident Management">
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <Panel title="Incidents">
            {loading ? (
              <EmptyState message="Loading…" />
            ) : incidents.length === 0 ? (
              <EmptyState message="No incidents recorded." />
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-xs">
                <thead>
                  <tr className="text-left text-ink-700/50 border-b border-line">
                    <th className="font-medium pb-1.5">ID</th>
                    <th className="font-medium pb-1.5">Title</th>
                    <th className="font-medium pb-1.5">Severity</th>
                    <th className="font-medium pb-1.5">Service</th>
                    <th className="font-medium pb-1.5">Status</th>
                    <th className="font-medium pb-1.5">Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((inc) => (
                    <tr
                      key={inc.id}
                      onClick={() => setSelected(inc)}
                      className={`border-b border-line last:border-0 hover:bg-surface-50 cursor-pointer ${
                        selected?.id === inc.id ? "bg-accent-tint" : ""
                      }`}
                    >
                      <td className="py-1.5 pr-2 font-mono text-ink-950">{inc.code}</td>
                      <td className="py-1.5 pr-2">{inc.title}</td>
                      <td className="py-1.5 pr-2"><SeverityBadge severity={inc.severity} /></td>
                      <td className="py-1.5 pr-2 text-ink-700/60">{inc.service}</td>
                      <td className="py-1.5 pr-2"><StatusPill status={inc.status === "RESOLVED" ? "healthy" : "warning"} /></td>
                      <td className="py-1.5 text-ink-700/50">{new Date(inc.detected_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </Panel>
        </div>

        <Panel title="Incident Detail">
          {!selected ? (
            <EmptyState message="Select an incident to view details." />
          ) : (
            <div className="space-y-3 text-xs">
              <div>
                <div className="text-sm font-semibold font-mono text-ink-950">{selected.code}</div>
                <div className="text-ink-700/70">{selected.title}</div>
              </div>
              <div className="flex gap-1.5">
                <SeverityBadge severity={selected.severity} />
                <StatusPill status={selected.status === "RESOLVED" ? "healthy" : "warning"} />
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Root Cause</div>
                <p className="text-ink-950 leading-relaxed">{selected.root_cause}</p>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Affected Service</div>
                <p>{selected.service}</p>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Detected</div>
                <p>{new Date(selected.detected_at).toLocaleString()}</p>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}
