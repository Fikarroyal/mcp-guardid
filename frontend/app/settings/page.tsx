"use client";

import { AppShell } from "@/components/AppShell";
import { Panel } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { session } = useAuth();

  return (
    <AppShell title="Settings">
      <div className="grid grid-cols-2 gap-3">
        <Panel title="Session">
          <dl className="text-xs space-y-2">
            <div className="flex justify-between"><dt className="text-ink-700/50">Name</dt><dd>{session?.fullName}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">Role</dt><dd>{session?.role}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">User ID</dt><dd className="font-mono text-[10.5px]">{session?.userId}</dd></div>
          </dl>
        </Panel>
        <Panel title="Environment">
          <dl className="text-xs space-y-2">
            <div className="flex justify-between"><dt className="text-ink-700/50">API Base URL</dt><dd className="font-mono text-[10.5px]">{process.env.NEXT_PUBLIC_API_BASE_URL}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">Vector Store Backend</dt><dd>local (numpy)</dd></div>
            <div className="flex justify-between"><dt className="text-ink-700/50">LLM Provider</dt><dd>mock / anthropic (env-configurable)</dd></div>
          </dl>
        </Panel>
      </div>
    </AppShell>
  );
}
