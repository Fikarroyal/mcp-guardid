"use client";

import { useAuth } from "@/lib/auth-context";
import { LogOut } from "lucide-react";

export function TopBar({ title }: { title: string }) {
  const { session, logout } = useAuth();

  return (
    <header className="h-14 border-b border-line bg-white flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="text-[13.5px] font-semibold text-ink-950">{title}</div>
      <div className="flex items-center gap-4">
        <span className="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-sm bg-status-healthyBg text-status-healthy font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          Production
        </span>
        {session && (
          <div className="flex items-center gap-3 pl-4 border-l border-line">
            <div className="text-right leading-tight">
              <div className="text-xs font-medium text-ink-950">{session.fullName}</div>
              <div className="text-[10.5px] text-ink-700/60">{session.role}</div>
            </div>
            <button
              onClick={logout}
              className="text-ink-700/50 hover:text-status-critical transition-colors"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
