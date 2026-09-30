"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState, Select } from "@/components/ui";
import { StatusPill } from "@/components/badges";
import { Field, GhostButton, Modal, PrimaryButton, inputCls } from "@/components/Modal";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ADMIN_ROLES, ALL_ROLES, type AdminUser } from "@/lib/types";

type FormState = { id?: string; email: string; full_name: string; password: string; role_name: string; department: string };
const EMPTY: FormState = { email: "", full_name: "", password: "", role_name: "Viewer", department: "" };

export default function AccountsPage() {
  const { session } = useAuth();
  const isAdmin = !!session && ADMIN_ROLES.includes(session.role);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [form, setForm] = useState<FormState | null>(null);
  const [toDelete, setToDelete] = useState<AdminUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setUsers((await api.listUsers()) as AdminUser[]);
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () =>
      users.filter(
        (u) =>
          (!roleFilter || u.role_name === roleFilter) &&
          (!search || `${u.full_name} ${u.email}`.toLowerCase().includes(search.toLowerCase()))
      ),
    [users, search, roleFilter]
  );

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    try {
      if (form.id) {
        const body: Record<string, unknown> = { full_name: form.full_name, role_name: form.role_name, department: form.department };
        if (form.password) body.password = form.password;
        await api.updateUser(form.id, body);
      } else {
        await api.createUser({ ...form, department: form.department || null });
      }
      setForm(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(u: AdminUser) {
    setError(null);
    try {
      await api.updateUser(u.id, { is_active: !u.is_active });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengubah status.");
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    setBusy(true);
    try {
      await api.deleteUser(toDelete.id);
      setToDelete(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menghapus.");
      setToDelete(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Accounts">
      <div className="flex items-center gap-2 mb-3">
        <input
          placeholder="Cari nama atau email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-line rounded-sm px-2.5 py-1.5 text-sm outline-none focus:border-accent w-64"
        />
        <Select compact fullWidth={false} value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="">Semua role</option>
          {ALL_ROLES.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </Select>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-ink-700/50">{filtered.length} akun</span>
          {isAdmin && (
            <PrimaryButton onClick={() => { setError(null); setForm(EMPTY); }}>
              <span className="inline-flex items-center gap-1"><Plus size={13} /> Tambah akun</span>
            </PrimaryButton>
          )}
        </div>
      </div>

      {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-3 py-2 mb-3">{error}</div>}
      {!isAdmin && (
        <div className="text-xs text-ink-700/60 bg-surface-100 rounded-sm px-3 py-2 mb-3">
          Anda dapat melihat daftar akun. Menambah, mengubah, dan menghapus hanya untuk Infrastructure Administrator dan Enterprise Administrator.
        </div>
      )}

      <Panel title="Daftar Akun">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : filtered.length === 0 ? (
          <EmptyState message="Tidak ada akun yang cocok." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Nama</th>
                <th className="font-medium pb-1.5">Email</th>
                <th className="font-medium pb-1.5">Role, Departemen</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5">Dibuat</th>
                {isAdmin && <th className="font-medium pb-1.5 text-right">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-b border-line last:border-0 hover:bg-surface-50 row-in">
                  <td className="py-2 pr-2 font-medium text-ink-950">{u.full_name}</td>
                  <td className="py-2 pr-2 font-mono text-[11px] text-ink-700/70">{u.email}</td>
                  <td className="py-2 pr-2">{u.department ? `${u.role_name}, ${u.department}` : u.role_name}</td>
                  <td className="py-2 pr-2"><StatusPill status={u.is_active ? "healthy" : "critical"} /></td>
                  <td className="py-2 pr-2 text-ink-700/50">{new Date(u.created_at).toLocaleDateString()}</td>
                  {isAdmin && (
                    <td className="py-2 text-right space-x-1.5 whitespace-nowrap">
                      <GhostButton onClick={() => { setError(null); setForm({ id: u.id, email: u.email, full_name: u.full_name, password: "", role_name: u.role_name, department: u.department ?? "" }); }}>Edit</GhostButton>
                      <GhostButton onClick={() => toggleActive(u)}>{u.is_active ? "Nonaktifkan" : "Aktifkan"}</GhostButton>
                      <GhostButton danger onClick={() => setToDelete(u)}>Hapus</GhostButton>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      {form && (
        <Modal title={form.id ? "Edit akun" : "Tambah akun"} onClose={() => setForm(null)}>
          <form onSubmit={save} className="space-y-3">
            <Field label="Nama lengkap">
              <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className={inputCls} />
            </Field>
            <Field label="Email">
              <input type="email" required disabled={!!form.id} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={`${inputCls} disabled:bg-surface-100`} />
            </Field>
            <Field label={form.id ? "Password baru (kosongkan jika tidak diubah)" : "Password"}>
              <input type="password" required={!form.id} minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputCls} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Role">
                <Select value={form.role_name} onChange={(e) => setForm({ ...form, role_name: e.target.value })}>
                  {ALL_ROLES.map((r) => <option key={r}>{r}</option>)}
                </Select>
              </Field>
              <Field label="Departemen">
                <input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className={inputCls} />
              </Field>
            </div>
            {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-2.5 py-1.5">{error}</div>}
            <div className="flex gap-2 justify-end pt-1">
              <GhostButton type="button" onClick={() => setForm(null)}>Batal</GhostButton>
              <PrimaryButton type="submit" disabled={busy}>{busy ? "Menyimpan…" : "Simpan"}</PrimaryButton>
            </div>
          </form>
        </Modal>
      )}

      {toDelete && (
        <Modal title="Hapus akun" onClose={() => setToDelete(null)} width={380}>
          <p className="text-xs text-ink-700/70 mb-4">
            Hapus permanen akun <b>{toDelete.full_name}</b> ({toDelete.email}, {toDelete.role_name})? Tindakan ini tidak dapat dibatalkan.
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
