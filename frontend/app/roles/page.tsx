"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState, Select } from "@/components/ui";
import { RiskBadge } from "@/components/badges";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { ALL_CATEGORIES, type PermissionItem, type RoleItem } from "@/lib/types";

const RISKS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function RolesPage() {
  const { session } = useAuth();
  const canEdit = session?.role === "Enterprise Administrator";
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [perms, setPerms] = useState<PermissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    const [r, p] = await Promise.all([api.listRoles(), api.listPermissions()]);
    setRoles(r as RoleItem[]);
    setPerms(p as PermissionItem[]);
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function run(fn: () => Promise<unknown>, okMessage: string) {
    setError(null);
    setNotice(null);
    try {
      await fn();
      await load();
      setNotice(okMessage);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Perubahan gagal.");
    }
  }

  const allowed = (role: string, cat: string) => perms.find((p) => p.role_name === role && p.category === cat)?.allowed ?? true;

  return (
    <AppShell title="Roles & Permissions">
      <p className="text-xs text-ink-700/60 mb-3 max-w-3xl">
        Perubahan di halaman ini langsung diberlakukan oleh Policy Engine pada request berikutnya. Aturan dasar tidak bisa dilemahkan dari sini: aksi HIGH dan CRITICAL tetap selalu butuh approval, dan CRITICAL tetap hanya untuk role elevated.
      </p>
      {!canEdit && (
        <div className="text-xs text-ink-700/60 bg-surface-100 rounded-sm px-3 py-2 mb-3">Mode baca saja. Hanya Enterprise Administrator yang dapat mengubah.</div>
      )}
      {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-3 py-2 mb-3">{error}</div>}
      {notice && <div className="text-xs text-status-healthy bg-status-healthyBg rounded-sm px-3 py-2 mb-3">{notice}</div>}

      <Panel title="Batas Risiko per Role">
        {loading ? (
          <EmptyState message="Loading…" />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Role</th>
                <th className="font-medium pb-1.5">Elevated</th>
                <th className="font-medium pb-1.5">Risiko maksimum</th>
                <th className="font-medium pb-1.5">Ubah</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="py-2 font-medium text-ink-950">{r.name}</td>
                  <td className="py-2 text-ink-700/60">{r.is_elevated ? "Ya" : "Tidak"}</td>
                  <td className="py-2"><RiskBadge risk={r.max_risk_level} /></td>
                  <td className="py-2">
                    <Select
                      compact
                      fullWidth={false}
                      disabled={!canEdit || r.name === session?.role}
                      value={r.max_risk_level}
                      onChange={(e) => run(() => api.updateRole(r.id, { max_risk_level: e.target.value }), `Batas risiko ${r.name} diubah ke ${e.target.value}.`)}
                    >
                      {RISKS.map((x) => <option key={x}>{x}</option>)}
                    </Select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>

      <div className="mt-4">
        <Panel title="Akses Kategori Tool (centang = diizinkan)">
          <p className="text-[11px] text-ink-700/50 mb-3">
            Hapus centang untuk memblokir seluruh tool dalam kategori itu bagi role tersebut, walaupun required_roles pada tool sebenarnya mengizinkan.
          </p>
          {loading ? (
            <EmptyState message="Loading…" />
          ) : (
            <div className="overflow-x-auto">
              <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-xs">
                <thead>
                  <tr className="text-left text-ink-700/50 border-b border-line">
                    <th className="font-medium pb-1.5">Role</th>
                    {ALL_CATEGORIES.map((c) => <th key={c} className="font-medium pb-1.5 text-center capitalize">{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {roles.map((r) => (
                    <tr key={r.id} className="border-b border-line last:border-0">
                      <td className="py-2 font-medium">{r.name}</td>
                      {ALL_CATEGORIES.map((c) => (
                        <td key={c} className="py-2 text-center">
                          <input
                            type="checkbox"
                            disabled={!canEdit || r.name === session?.role}
                            checked={allowed(r.name, c)}
                            onChange={(e) => run(() => api.setPermission(r.name, c, e.target.checked), `${r.name}, ${c}: ${e.target.checked ? "diizinkan" : "diblokir"}.`)}
                            className="accent-[#3452E1] disabled:opacity-40"
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}
