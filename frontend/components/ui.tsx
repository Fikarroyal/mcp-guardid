import { ReactNode } from "react";
import { ChevronDown, LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  sublabel,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string;
  sublabel?: string;
  icon?: LucideIcon;
  tone?: "default" | "healthy" | "warning" | "critical";
}) {
  const toneClass =
    tone === "healthy"
      ? "text-status-healthy"
      : tone === "warning"
      ? "text-status-warning"
      : tone === "critical"
      ? "text-status-critical"
      : "text-ink-950";
  return (
    <div className="border border-line bg-white rounded-sm px-4 py-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-ink-700/60 font-medium">{label}</span>
        {Icon && <Icon size={14} className="text-ink-700/40" strokeWidth={2} />}
      </div>
      <div className={`text-xl font-semibold tabular tracking-tight ${toneClass}`}>{value}</div>
      {sublabel && <div className="text-[11px] text-ink-700/45 mt-0.5">{sublabel}</div>}
    </div>
  );
}

export function Panel({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="border border-line bg-white rounded-sm">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-line">
        <h2 className="text-[12.5px] font-semibold text-ink-950">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="text-xs text-ink-700/45 py-6 text-center">{message}</div>;
}

export function Select({
  className = "",
  compact = false,
  fullWidth = true,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { compact?: boolean; fullWidth?: boolean }) {
  const base = compact
    ? "border border-line rounded-sm py-1.5 text-xs"
    : "w-full border border-line rounded-sm px-2.5 py-1.5 text-sm";
  return (
    <div className={`relative ${fullWidth ? "w-full" : "inline-block"}`}>
      <select
        {...props}
        className={`appearance-none bg-white pr-8 ${compact ? "pl-2.5" : ""} ${base} outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        strokeWidth={2}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-700/40"
      />
    </div>
  );
}
