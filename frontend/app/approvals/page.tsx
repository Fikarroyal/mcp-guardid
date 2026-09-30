"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState } from "@/components/ui";
import { RiskBadge, StatusPill } from "@/components/badges";
import { api, ApiError } from "@/lib/api";
import type { Approval } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirmTarget, setConfirmTarget] = useState<{ approval: Approval; action: "approve" | "reject" } | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    const data = (await api.listApprovals()) as Approval[];
    setApprovals(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function decide() {
    if (!confirmTarget) return;
    setBusy(true);
    setMessage(null);
    try {
      if (confirmTarget.action === "approve") {
        await api.approveApproval(confirmTarget.approval.id, note);
        setMessage(`Approved, ${confirmTarget.approval.tool_name} executed via MCP Gateway.`);
      } else {
        await api.rejectApproval(confirmTarget.approval.id, note);
        setMessage(`Rejected ${confirmTarget.approval.tool_name}.`);
      }
      setConfirmTarget(null);
      setNote("");
      await load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  const pending = approvals.filter((a) => a.status === "PENDING");
  const decided = approvals.filter((a) => a.status !== "PENDING");

  return (
    <AppShell title="Approval Center">
      {message && <div className="text-xs bg-status-infoBg text-status-info rounded-sm px-3 py-2 mb-4">{message}</div>}

      <Panel title={`Pending Approvals (${pending.length})`}>
        {loading ? (
          <EmptyState message="Loading…" />
        ) : pending.length === 0 ? (
          <EmptyState message="No pending approvals." />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {pending.map((a) => (
              <div key={a.id} className="border border-line rounded-sm p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10.5px] font-medium uppercase tracking-wide text-status-warning">
                    {a.risk_level} Risk Action
                  </span>
                  <RiskBadge risk={a.risk_level} />
                </div>
                <div className="text-sm font-mono font-medium text-ink-950 mb-2">{a.tool_name}</div>
                <dl className="text-[11px] space-y-1 mb-3">
                  <div className="flex justify-between"><dt className="text-ink-700/50">Target</dt><dd>{a.target || " "}</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-700/50">Reason</dt><dd className="text-right max-w-[60%] truncate" title={a.reason}>{a.reason}</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-700/50">Requested by</dt><dd>{a.requested_by_role}</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-700/50">Required role</dt><dd>{a.required_role}</dd></div>
                  <div className="flex justify-between"><dt className="text-ink-700/50">Requested at</dt><dd>{new Date(a.requested_at).toLocaleTimeString()}</dd></div>
                </dl>
                <div className="flex gap-2">
                  <button
                    onClick={() => setConfirmTarget({ approval: a, action: "approve" })}
                    className="flex-1 bg-status-healthy text-white text-xs font-medium rounded-sm py-1.5 hover:opacity-90"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => setConfirmTarget({ approval: a, action: "reject" })}
                    className="flex-1 border border-line text-ink-700 text-xs font-medium rounded-sm py-1.5 hover:border-status-critical hover:text-status-critical"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="mt-4">
        <Panel title="Decision History">
          {decided.length === 0 ? (
            <EmptyState message="No decisions recorded yet." />
          ) : (
            <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-xs">
              <thead>
                <tr className="text-left text-ink-700/50 border-b border-line">
                  <th className="font-medium pb-1.5">Tool</th>
                  <th className="font-medium pb-1.5">Risk</th>
                  <th className="font-medium pb-1.5">Requested By</th>
                  <th className="font-medium pb-1.5">Status</th>
                  <th className="font-medium pb-1.5">Decided At</th>
                </tr>
              </thead>
              <tbody>
                {decided.map((a) => (
                  <tr key={a.id} className="border-b border-line last:border-0">
                    <td className="py-1.5 font-mono">{a.tool_name}</td>
                    <td className="py-1.5"><RiskBadge risk={a.risk_level} /></td>
                    <td className="py-1.5 text-ink-700/60">{a.requested_by_role}</td>
                    <td className="py-1.5"><StatusPill status={a.status} /></td>
                    <td className="py-1.5 text-ink-700/50">{a.decided_at ? new Date(a.decided_at).toLocaleString() : " "}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </Panel>
      </div>

      {confirmTarget && (
        <div className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center">
          <div className="bg-white rounded-sm p-5 w-[380px]">
            <h3 className="text-sm font-semibold mb-1">
              {confirmTarget.action === "approve" ? "Confirm approval" : "Confirm rejection"}
            </h3>
            <p className="text-xs text-ink-700/60 mb-3">
              {confirmTarget.action === "approve"
                ? `This will execute "${confirmTarget.approval.tool_name}" immediately via the MCP Gateway.`
                : `This will permanently reject the request for "${confirmTarget.approval.tool_name}".`}
            </p>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Decision note (optional)"
              className="w-full border border-line rounded-sm px-2.5 py-1.5 text-xs mb-3 outline-none focus:border-accent"
              rows={2}
            />
            <div className="flex gap-2">
              <button
                onClick={decide}
                disabled={busy}
                className={`flex-1 text-white text-xs font-medium rounded-sm py-1.5 ${
                  confirmTarget.action === "approve" ? "bg-status-healthy" : "bg-status-critical"
                } disabled:opacity-50`}
              >
                {busy ? "Processing…" : confirmTarget.action === "approve" ? "Approve & Execute" : "Reject"}
              </button>
              <button
                onClick={() => setConfirmTarget(null)}
                className="flex-1 border border-line text-xs font-medium rounded-sm py-1.5"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
