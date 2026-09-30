"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Route,
  Boxes,
  ShieldCheck,
  AlertTriangle,
  ClipboardList,
  BookOpen,
  FlaskConical,
  ShieldAlert,
  Settings,
  Server,
  Users,
  KeyRound,
  UserCog,
  ScrollText,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/routing", label: "Tool Routing", icon: Route },
  { href: "/registry", label: "Tool Registry", icon: Boxes },
  { href: "/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck },
  { href: "/audit", label: "Audit Trail", icon: ClipboardList },
  { href: "/rag", label: "RAG Knowledge", icon: BookOpen },
  { href: "/evaluation", label: "Evaluations", icon: FlaskConical },
  { href: "/security", label: "Security", icon: ShieldAlert },
  { href: "/accounts", label: "Accounts", icon: Users },
  { href: "/api-keys", label: "API Keys", icon: KeyRound },
  { href: "/roles", label: "Roles & Permissions", icon: UserCog },
  { href: "/executions", label: "Execution Log", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[216px] bg-ink-950 text-surface-100 flex flex-col z-20">
      <div className="h-14 flex items-center gap-2 px-4 border-b border-white/10">
        <Server size={17} strokeWidth={2.25} className="text-accent" />
        <div className="leading-tight">
          <div className="text-[13px] font-semibold tracking-tight text-white">MCP-GuardID</div>
          <div className="text-[10px] text-white/40 -mt-0.5">Infra Control Platform</div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 mx-2 px-2.5 py-1.5 rounded-sm text-[12.5px] mb-0.5 transition-colors ${
                active ? "bg-white/10 text-white" : "text-white/55 hover:text-white/90 hover:bg-white/5"
              }`}
            >
              <Icon size={15} strokeWidth={2} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-white/10 text-[10px] text-white/35">
        v1.0.0 &middot; MCP Gateway: online
      </div>
    </aside>
  );
}
