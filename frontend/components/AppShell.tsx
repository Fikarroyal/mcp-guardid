"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, session, router]);

  if (loading || !session) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-ink-700/50">Loading…</div>;
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <div className="ml-[216px]">
        <TopBar title={title} />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
