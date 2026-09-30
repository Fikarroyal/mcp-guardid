"use client";

import { FormEvent, useEffect, useState } from "react";
import { Copy, Plus } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState } from "@/components/ui";
import { StatusPill } from "@/components/badges";
import { Field, GhostButton, Modal, PrimaryButton, inputCls } from "@/components/Modal";
import { Select } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ADMIN_ROLES, ALL_ROLES, type ApiKeyCreated, type ApiKeyItem } from "@/lib/types";

export default function ApiKeysPage() {
  const { session } = useAuth();
  const isAdmin = !!session && ADMIN_ROLES.includes(session.role);
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("Viewer");
  const [expiry, setExpiry] = useState("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function load() {
    if (!isAdmin) return setLoading(false);
    setLoading(true);
    try {
      setKeys((await api.listApiKeys()) as ApiKeyItem[]);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = (await api.createApiKey({ name, role_name: role, expires_in_days: expiry ? Number(expiry) : null })) as ApiKeyCreated;
      setCreating(false);
      setName("");
      setExpiry("");
      setCreated(res);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal membuat key.");
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Aksi gagal.");
    }
  }

  if (!isAdmin) {
    return (
      <AppShell title="API Keys">
        <Panel title="API Keys">
          <EmptyState message="Halaman ini hanya untuk Infrastructure Administrator dan Enterprise Administrator." />
        </Panel>
      </AppShell>
    );
  }

  return (
    <AppShell title="API Keys">
      <div className="flex items-center mb-3">
        <p className="text-xs text-ink-700/60 max-w-xl">
          Token service account untuk otomasi (CI, script, integrasi). Setiap key bertindak dengan role yang dipilih dan tunduk pada RBAC serta approval yang sama seperti user biasa. Gunakan sebagai header <span className="font-mono">Authorization: Bearer gid_…</span>
        </p>
        <div className="ml-auto">
          <PrimaryButton onClick={() => { setError(null); setCreating(true); }}>
            <span className="inline-flex items-center gap-1"><Plus size={13} /> Buat API key</span>
          </PrimaryButton>
        </div>
      </div>
      {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-3 py-2 mb-3">{error}</div>}

      <Panel title="Daftar API Key">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : keys.length === 0 ? (
          <EmptyState message="Belum ada API key." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Nama</th>
                <th className="font-medium pb-1.5">Key</th>
                <th className="font-medium pb-1.5">Role</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5">Terakhir dipakai</th>
                <th className="font-medium pb-1.5">Kedaluwarsa</th>
                <th className="font-medium pb-1.5 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} className="border-b border-line last:border-0 row-in">
                  <td className="py-2 pr-2 font-medium text-ink-950">{k.name}</td>
                  <td className="py-2 pr-2 font-mono text-[11px] text-ink-700/70">{k.key_prefix}</td>
                  <td className="py-2 pr-2">{k.role_name}</td>
                  <td className="py-2 pr-2"><StatusPill status={k.is_active ? "healthy" : "critical"} /></td>
                  <td className="py-2 pr-2 text-ink-700/50">{k.last_used ? new Date(k.last_used).toLocaleString() : "Belum pernah"}</td>
                  <td className="py-2 pr-2 text-ink-700/50">{k.expires_at ? new Date(k.expires_at).toLocaleDateString() : "Tidak ada"}</td>
                  <td className="py-2 text-right space-x-1.5 whitespace-nowrap">
                    {k.is_active && <GhostButton onClick={() => act(() => api.revokeApiKey(k.id))}>Cabut</GhostButton>}
                    <GhostButton danger onClick={() => act(() => api.deleteApiKey(k.id))}>Hapus</GhostButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      {creating && (
        <Modal title="Buat API key" onClose={() => setCreating(false)}>
          <form onSubmit={create} className="space-y-3">
            <Field label="Nama (misal: ci-pipeline)">
              <input required value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
            </Field>
            <Field label="Role">
              <Select value={role} onChange={(e) => setRole(e.target.value)}>
                {ALL_ROLES.map((r) => <option key={r}>{r}</option>)}
              </Select>
            </Field>
            <Field label="Kedaluwarsa dalam hari (kosongkan jika tidak ada)">
              <input type="number" min={1} value={expiry} onChange={(e) => setExpiry(e.target.value)} className={inputCls} />
            </Field>
            {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-2.5 py-1.5">{error}</div>}
            <div className="flex gap-2 justify-end">
              <GhostButton type="button" onClick={() => setCreating(false)}>Batal</GhostButton>
              <PrimaryButton type="submit" disabled={busy}>{busy ? "Membuat…" : "Buat"}</PrimaryButton>
            </div>
          </form>
        </Modal>
      )}

      {created && (
        <Modal title="API key berhasil dibuat" onClose={() => { setCreated(null); setCopied(false); }} width={480}>
          <p className="text-xs text-status-warning bg-status-warningBg rounded-sm px-2.5 py-2 mb-3">
            Salin key ini sekarang. Demi keamanan, key lengkap hanya ditampilkan sekali dan tidak dapat dilihat lagi.
          </p>
          <div className="flex items-center gap-2 border border-line rounded-sm p-2 bg-surface-50">
            <code className="text-[11px] break-all flex-1 font-mono">{created.raw_key}</code>
            <GhostButton onClick={async () => { await navigator.clipboard.writeText(created.raw_key); setCopied(true); }}>
              <span className="inline-flex items-center gap-1"><Copy size={12} /> {copied ? "Tersalin" : "Salin"}</span>
            </GhostButton>
          </div>
          <div className="flex justify-end mt-4">
            <PrimaryButton onClick={() => { setCreated(null); setCopied(false); }}>Selesai</PrimaryButton>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
