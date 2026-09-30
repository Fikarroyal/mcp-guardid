"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState, Select } from "@/components/ui";
import { PermissionBadge, RiskBadge, StatusPill } from "@/components/badges";
import { api } from "@/lib/api";
import type { AuditLog } from "@/lib/types";

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<AuditLog | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const data = (await api.listAudit({
        risk: riskFilter || undefined,
        status_filter: statusFilter || undefined,
        limit: 200,
      })) as AuditLog[];
      setLogs(data);
      setLoading(false);
    })();
  }, [riskFilter, statusFilter]);

  return (
    <AppShell title="Audit Trail">
      <div className="flex items-center gap-2 mb-3">
        <Select compact fullWidth={false} value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
          <option value="">All risk levels</option>
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </Select>
        <Select compact fullWidth={false} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="BLOCKED">Blocked</option>
          <option value="PENDING_APPROVAL">Pending Approval</option>
        </Select>
        <div className="ml-auto text-xs text-ink-700/50">{logs.length} records</div>
      </div>

      <Panel title="Request Log">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : logs.length === 0 ? (
          <EmptyState message="No audit records match this filter." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Timestamp</th>
                <th className="font-medium pb-1.5">User Role</th>
                <th className="font-medium pb-1.5">Intent</th>
                <th className="font-medium pb-1.5">Risk</th>
                <th className="font-medium pb-1.5">Permission</th>
                <th className="font-medium pb-1.5">Approval</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5 text-right">Latency</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr
                  key={log.id}
                  onClick={() => setSelected(log)}
                  className="border-b border-line last:border-0 hover:bg-surface-50 cursor-pointer"
                >
                  <td className="py-1.5 pr-2 text-ink-700/60 whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="py-1.5 pr-2">{log.user_role}</td>
                  <td className="py-1.5 pr-2 text-ink-700/70">{log.detected_intent}</td>
                  <td className="py-1.5 pr-2"><RiskBadge risk={log.risk_level} /></td>
                  <td className="py-1.5 pr-2"><PermissionBadge permission={log.permission_result} /></td>
                  <td className="py-1.5 pr-2 text-ink-700/60">{log.approval_status}</td>
                  <td className="py-1.5 pr-2"><StatusPill status={log.status} /></td>
                  <td className="py-1.5 text-right tabular">{log.execution_latency_ms.toFixed(0)}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      {selected && (
        <div className="fixed inset-0 bg-black/20 z-30 flex justify-end" onClick={() => setSelected(null)}>
          <div className="w-[440px] bg-white h-full overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold">Request Detail</h3>
              <button onClick={() => setSelected(null)} className="text-ink-700/40 hover:text-ink-950">
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Query</div>
                <div className="text-ink-950">{selected.user_query}</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Intent</div>{selected.detected_intent}</div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Risk</div><RiskBadge risk={selected.risk_level} /></div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Permission</div><PermissionBadge permission={selected.permission_result} /></div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Status</div><StatusPill status={selected.status} /></div>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Candidate Tools</div>
                <div className="flex flex-wrap gap-1">
                  {selected.candidate_tools.map((t) => (
                    <span key={t} className="bg-surface-100 px-1.5 py-0.5 rounded-sm font-mono text-[10.5px]">{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Selected Tools</div>
                <div className="flex flex-wrap gap-1">
                  {selected.selected_tools.map((t) => (
                    <span key={t} className="bg-accent-tint text-accent px-1.5 py-0.5 rounded-sm font-mono text-[10.5px]">{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Final Response</div>
                <p className="text-ink-950 leading-relaxed whitespace-pre-line">{selected.final_response}</p>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Request ID</div>
                <div className="font-mono text-[10.5px] text-ink-700/60">{selected.request_id}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
