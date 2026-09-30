"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Plus, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState, Select } from "@/components/ui";
import { RiskBadge, StatusPill } from "@/components/badges";
import { Field, GhostButton, Modal, PrimaryButton, inputCls } from "@/components/Modal";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ADMIN_ROLES, ALL_CATEGORIES, ALL_ROLES, type Tool } from "@/lib/types";

const RISKS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
type Form = {
  id?: string;
  name: string;
  description: string;
  category: string;
  risk_level: string;
  required_roles: string[];
  timeout_seconds: number;
  enabled: boolean;
  version: string;
};
const EMPTY: Form = {
  name: "", description: "", category: "server", risk_level: "LOW", required_roles: [], timeout_seconds: 30, enabled: true, version: "1.0.0",
};

export default function ToolRegistryPage() {
  const { session } = useAuth();
  const isAdmin = !!session && ADMIN_ROLES.includes(session.role);
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Tool | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [toDelete, setToDelete] = useState<Tool | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setTools((await api.listTools()) as Tool[]);
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () => tools.filter((t) => (category === "all" || t.category === category) && (!search || t.name.toLowerCase().includes(search.toLowerCase()))),
    [tools, category, search]
  );

  function openEdit(t: Tool) {
    setError(null);
    setForm({ id: t.id, name: t.name, description: t.description, category: t.category, risk_level: t.risk_level,
      required_roles: t.required_roles, timeout_seconds: 30, enabled: t.enabled, version: t.version });
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    try {
      if (form.id) {
        await api.updateTool(form.id, {
          description: form.description, category: form.category, risk_level: form.risk_level,
          required_roles: form.required_roles, timeout_seconds: form.timeout_seconds, enabled: form.enabled, version: form.version,
        });
      } else {
        await api.createTool({
          name: form.name, description: form.description, category: form.category, risk_level: form.risk_level,
          required_roles: form.required_roles, timeout_seconds: form.timeout_seconds,
          input_schema: { type: "object", properties: {}, required: [] }, output_schema: { type: "object" },
        });
      }
      setForm(null);
      setSelected(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan tool.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEnabled(t: Tool) {
    setError(null);
    try {
      const updated = (await api.updateTool(t.id, { enabled: !t.enabled })) as Tool;
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengubah status.");
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    setBusy(true);
    try {
      await api.deleteTool(toDelete.id);
      setToDelete(null);
      setSelected(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menghapus tool.");
      setToDelete(null);
    } finally {
      setBusy(false);
    }
  }

  const toggleRole = (role: string) =>
    form && setForm({ ...form, required_roles: form.required_roles.includes(role) ? form.required_roles.filter((r) => r !== role) : [...form.required_roles, role] });

  return (
    <AppShell title="Tool Registry">
      <div className="flex items-center gap-2 mb-3">
        <input placeholder="Cari nama tool" value={search} onChange={(e) => setSearch(e.target.value)}
          className="border border-line rounded-sm px-2.5 py-1.5 text-sm outline-none focus:border-accent w-64" />
        <div className="flex gap-1">
          {["all", ...ALL_CATEGORIES].map((c) => (
            <button key={c} onClick={() => setCategory(c)}
              className={`text-[11px] px-2.5 py-1.5 rounded-sm border transition-colors ${category === c ? "bg-ink-950 text-white border-ink-950" : "border-line text-ink-700/60 hover:border-accent"}`}>
              {c}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-ink-700/50">{filtered.length} tool</span>
          {isAdmin && (
            <PrimaryButton onClick={() => { setError(null); setForm(EMPTY); }}>
              <span className="inline-flex items-center gap-1"><Plus size={13} /> Tambah tool</span>
            </PrimaryButton>
          )}
        </div>
      </div>
      {error && !form && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-3 py-2 mb-3">{error}</div>}

      <Panel title="Registered Tools">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : filtered.length === 0 ? (
          <EmptyState message="Tidak ada tool yang cocok." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Tool</th>
                <th className="font-medium pb-1.5">Category</th>
                <th className="font-medium pb-1.5">Risk</th>
                <th className="font-medium pb-1.5">Required Role(s)</th>
                <th className="font-medium pb-1.5 text-right">Success Rate</th>
                <th className="font-medium pb-1.5 text-right">Avg Latency</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5">Version</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr key={t.id} onClick={() => setSelected(t)} className="border-b border-line last:border-0 hover:bg-surface-50 cursor-pointer row-in">
                  <td className="py-1.5 pr-2 font-medium text-ink-950 font-mono">{t.name}</td>
                  <td className="py-1.5 pr-2 text-ink-700/70 capitalize">{t.category}</td>
                  <td className="py-1.5 pr-2"><RiskBadge risk={t.risk_level} /></td>
                  <td className="py-1.5 pr-2 text-ink-700/60 max-w-[240px] truncate">{t.required_roles.join(", ")}</td>
                  <td className="py-1.5 pr-2 text-right tabular">{t.success_rate.toFixed(1)}%</td>
                  <td className="py-1.5 pr-2 text-right tabular">{t.avg_latency_ms.toFixed(0)}ms</td>
                  <td className="py-1.5 pr-2"><StatusPill status={t.enabled ? "healthy" : "critical"} /></td>
                  <td className="py-1.5 text-ink-700/50 font-mono">{t.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      {selected && !form && (
        <div className="fixed inset-0 bg-black/20 z-30 flex justify-end" onClick={() => setSelected(null)}>
          <div className="w-[420px] bg-white h-full overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold font-mono text-ink-950">{selected.name}</h3>
              <button onClick={() => setSelected(null)} className="text-ink-700/40 hover:text-ink-950"><X size={16} /></button>
            </div>
            <div className="flex gap-1.5 mb-4">
              <RiskBadge risk={selected.risk_level} />
              <StatusPill status={selected.enabled ? "healthy" : "critical"} />
              {selected.requires_approval && <StatusPill status="PENDING" />}
            </div>
            <p className="text-xs text-ink-700/70 leading-relaxed mb-4">{selected.description}</p>
            {isAdmin && (
              <div className="flex gap-2 mb-5">
                <GhostButton onClick={() => openEdit(selected)}>Edit</GhostButton>
                <GhostButton onClick={() => toggleEnabled(selected)}>{selected.enabled ? "Nonaktifkan" : "Aktifkan"}</GhostButton>
                <GhostButton danger onClick={() => setToDelete(selected)}>Hapus</GhostButton>
              </div>
            )}
            <div className="space-y-3 text-xs">
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Required Roles</div>
                <div className="flex flex-wrap gap-1">
                  {selected.required_roles.map((r) => <span key={r} className="bg-surface-100 px-1.5 py-0.5 rounded-sm text-[11px]">{r}</span>)}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Success Rate</div><div className="tabular font-medium">{selected.success_rate.toFixed(1)}%</div></div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Avg Latency</div><div className="tabular font-medium">{selected.avg_latency_ms.toFixed(0)} ms</div></div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Executions</div><div className="tabular font-medium">{selected.execution_count}</div></div>
                <div><div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Version</div><div className="font-mono">{selected.version}</div></div>
              </div>
              <div>
                <div className="text-[10.5px] font-medium text-ink-700/50 uppercase mb-1">Input Schema</div>
                <pre className="bg-surface-50 rounded-sm p-2 text-[10.5px] overflow-x-auto">{JSON.stringify(selected.input_schema, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {form && (
        <Modal title={form.id ? `Edit ${form.name}` : "Tambah tool"} onClose={() => setForm(null)} width={500}>
          <form onSubmit={save} className="space-y-3">
            <Field label="Nama tool (huruf kecil dan underscore)">
              <input required disabled={!!form.id} pattern="[a-z][a-z0-9_]*" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={`${inputCls} font-mono disabled:bg-surface-100`} />
            </Field>
            <Field label="Deskripsi (dipakai untuk semantic retrieval)">
              <textarea required rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inputCls} />
            </Field>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Kategori">
                <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                  {ALL_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </Select>
              </Field>
              <Field label="Risk level">
                <Select value={form.risk_level} onChange={(e) => setForm({ ...form, risk_level: e.target.value })}>
                  {RISKS.map((r) => <option key={r}>{r}</option>)}
                </Select>
              </Field>
              <Field label="Timeout (detik)">
                <input type="number" min={1} value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })} className={inputCls} />
              </Field>
            </div>
            {(form.risk_level === "HIGH" || form.risk_level === "CRITICAL") && (
              <div className="text-[11px] text-status-warning bg-status-warningBg rounded-sm px-2.5 py-1.5">
                Tool {form.risk_level} otomatis wajib approval. Ini tidak bisa dimatikan.
              </div>
            )}
            <Field label="Role yang diizinkan (kosong = tidak dibatasi per tool)">
              <div className="grid grid-cols-2 gap-1">
                {ALL_ROLES.map((r) => (
                  <label key={r} className="flex items-center gap-1.5 text-xs">
                    <input type="checkbox" checked={form.required_roles.includes(r)} onChange={() => toggleRole(r)} className="accent-[#3452E1]" />
                    {r}
                  </label>
                ))}
              </div>
            </Field>
            {form.id && (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Versi"><input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} className={inputCls} /></Field>
                <Field label="Status">
                  <Select value={String(form.enabled)} onChange={(e) => setForm({ ...form, enabled: e.target.value === "true" })}>
                    <option value="true">Aktif</option>
                    <option value="false">Nonaktif</option>
                  </Select>
                </Field>
              </div>
            )}
            {!form.id && (
              <p className="text-[11px] text-ink-700/55">
                Tool baru langsung dapat ditemukan oleh semantic retrieval. Agar bisa dieksekusi, adapter infrastruktur untuk tool ini perlu diimplementasikan di mcp_server/tools/executor.py.
              </p>
            )}
            {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-2.5 py-1.5">{error}</div>}
            <div className="flex gap-2 justify-end">
              <GhostButton type="button" onClick={() => setForm(null)}>Batal</GhostButton>
              <PrimaryButton type="submit" disabled={busy}>{busy ? "Menyimpan…" : "Simpan"}</PrimaryButton>
            </div>
          </form>
        </Modal>
      )}

      {toDelete && (
        <Modal title="Hapus tool" onClose={() => setToDelete(null)} width={380}>
          <p className="text-xs text-ink-700/70 mb-4">
            Hapus permanen tool <b className="font-mono">{toDelete.name}</b> dari registry dan indeks pencarian? Tool tidak akan bisa dipilih agent lagi.
          </p>
          <div className="flex gap-2 justify-end">
            <GhostButton onClick={() => setToDelete(null)}>Batal</GhostButton>
            <button onClick={confirmDelete} disabled={busy} className="bg-status-critical text-white text-xs font-medium rounded-sm px-3.5 py-1.5 disabled:opacity-50">
              {busy ? "Menghapus…" : "Hapus"}
            </button>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
