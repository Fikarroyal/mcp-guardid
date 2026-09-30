"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState, Select } from "@/components/ui";
import { StatusPill } from "@/components/badges";
import { GhostButton, Modal, PrimaryButton } from "@/components/Modal";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ADMIN_ROLES, type Tool, type ToolExecution } from "@/lib/types";

export default function ExecutionLogPage() {
  const { session } = useAuth();
  const isAdmin = !!session && ADMIN_ROLES.includes(session.role);
  const [rows, setRows] = useState<ToolExecution[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [tool, setTool] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ToolExecution | null>(null);
  const [days, setDays] = useState(30);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setRows((await api.listExecutions(tool || undefined, status || undefined)) as ToolExecution[]);
    setLoading(false);
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool, status]);
  useEffect(() => {
    (async () => setTools((await api.listTools()) as Tool[]))();
  }, []);

  async function purge() {
    setError(null);
    try {
      const res = (await api.purgeExecutions(days)) as { deleted: number };
      setMessage(`${res.deleted} record lebih lama dari ${days} hari dihapus.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Purge gagal.");
    }
  }

  async function remove(row: ToolExecution) {
    setError(null);
    try {
      await api.deleteExecution(row.id);
      setSelected(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hapus gagal.");
    }
  }

  return (
    <AppShell title="Execution Log">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <Select compact fullWidth={false} value={tool} onChange={(e) => setTool(e.target.value)}>
          <option value="">Semua tool</option>
          {tools.map((t) => <option key={t.id}>{t.name}</option>)}
        </Select>
        <Select compact fullWidth={false} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Semua status</option>
          <option value="success">success</option>
          <option value="failed">failed</option>
          <option value="timeout">timeout</option>
        </Select>
        <span className="text-xs text-ink-700/50">{rows.length} record</span>
        {isAdmin && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-ink-700/60">Hapus record lebih lama dari</span>
            <input type="number" min={1} value={days} onChange={(e) => setDays(Number(e.target.value))} className="border border-line rounded-sm px-2 py-1 text-xs w-16" />
            <span className="text-xs text-ink-700/60">hari</span>
            <GhostButton danger onClick={purge}>Purge</GhostButton>
          </div>
        )}
      </div>
      {message && <div className="text-xs text-status-healthy bg-status-healthyBg rounded-sm px-3 py-2 mb-3">{message}</div>}
      {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-3 py-2 mb-3">{error}</div>}

      <Panel title="Riwayat Eksekusi MCP Gateway">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : rows.length === 0 ? (
          <EmptyState message="Belum ada eksekusi tool yang tercatat." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Waktu</th>
                <th className="font-medium pb-1.5">Execution ID</th>
                <th className="font-medium pb-1.5">Tool</th>
                <th className="font-medium pb-1.5">Target</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5 text-right">Latency</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} onClick={() => setSelected(r)} className="border-b border-line last:border-0 hover:bg-surface-50 cursor-pointer">
                  <td className="py-1.5 pr-2 text-ink-700/60 whitespace-nowrap">{new Date(r.timestamp).toLocaleString()}</td>
                  <td className="py-1.5 pr-2 font-mono">{r.execution_id}</td>
                  <td className="py-1.5 pr-2 font-mono">{r.tool_name}</td>
                  <td className="py-1.5 pr-2 text-ink-700/70">{r.target}</td>
                  <td className="py-1.5 pr-2"><StatusPill status={r.status} /></td>
                  <td className="py-1.5 text-right tabular">{r.latency_ms.toFixed(0)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      {selected && (
        <Modal title={`Eksekusi ${selected.execution_id}`} onClose={() => setSelected(null)} width={520}>
          <dl className="text-xs space-y-1.5 mb-3">
            <div className="flex justify-between"><dt className="text-ink-700/50">Tool</dt><dd className="font-mono">{selected.tool_name}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">Target</dt><dd>{selected.target}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">Sumber</dt><dd>{selected.source}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">Request ID</dt><dd className="font-mono text-[10.5px]">{selected.request_id}</dd></div>
          </dl>
          <pre className="bg-surface-50 rounded-sm p-2 text-[11px] overflow-x-auto mb-4">{JSON.stringify(selected.result, null, 2)}</pre>
          <div className="flex justify-end gap-2">
            {isAdmin && <GhostButton danger onClick={() => remove(selected)}>Hapus record</GhostButton>}
            <PrimaryButton onClick={() => setSelected(null)}>Tutup</PrimaryButton>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
