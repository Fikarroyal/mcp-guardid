"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Server } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Check API connectivity.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-[380px]">
        <div className="flex items-center gap-2 mb-6 justify-center">
          <Server size={20} className="text-accent" strokeWidth={2.25} />
          <span className="text-[15px] font-semibold text-ink-950 tracking-tight">MCP-GuardID</span>
        </div>

        <div className="border border-line bg-white rounded-sm p-6">
          <h1 className="text-[13.5px] font-semibold text-ink-950 mb-0.5">Sign in</h1>
          <p className="text-xs text-ink-700/55 mb-5">Enterprise IT Operations &amp; Security Console</p>

          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-ink-700/70 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.id"
                className="w-full border border-line rounded-sm px-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent/30"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-ink-700/70 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-line rounded-sm px-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent/30"
              />
            </div>
            {error && <div className="text-xs text-status-critical bg-status-criticalBg rounded-sm px-2.5 py-1.5">{error}</div>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-ink-950 text-white text-sm font-medium rounded-sm py-1.5 hover:bg-ink-800 transition-colors disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-ink-700/60 mt-4">
          Belum punya akun?{" "}
          <Link href="/register" className="text-accent font-medium hover:underline">
            Daftar akun
          </Link>
        </p>
      </div>
    </div>
  );
}
