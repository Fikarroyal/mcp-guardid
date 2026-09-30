const RISK_STYLES: Record<string, string> = {
  LOW: "text-status-healthy bg-status-healthyBg",
  MEDIUM: "text-status-warning bg-status-warningBg",
  HIGH: "text-status-critical bg-status-criticalBg",
  CRITICAL: "text-white bg-status-critical",
};

const PERMISSION_STYLES: Record<string, string> = {
  ALLOWED: "text-status-healthy bg-status-healthyBg",
  DENIED: "text-status-critical bg-status-criticalBg",
  APPROVAL_REQUIRED: "text-status-warning bg-status-warningBg",
};

const STATE_STYLES: Record<string, string> = {
  healthy: "text-status-healthy bg-status-healthyBg",
  success: "text-status-healthy bg-status-healthyBg",
  COMPLETED: "text-status-healthy bg-status-healthyBg",
  ALLOWED: "text-status-healthy bg-status-healthyBg",
  APPROVED: "text-status-healthy bg-status-healthyBg",
  warning: "text-status-warning bg-status-warningBg",
  degraded: "text-status-warning bg-status-warningBg",
  PENDING: "text-status-warning bg-status-warningBg",
  PENDING_APPROVAL: "text-status-warning bg-status-warningBg",
  critical: "text-status-critical bg-status-criticalBg",
  failed: "text-status-critical bg-status-criticalBg",
  BLOCKED: "text-status-critical bg-status-criticalBg",
  REJECTED: "text-status-critical bg-status-criticalBg",
  DENIED: "text-status-critical bg-status-criticalBg",
  timeout: "text-status-warning bg-status-warningBg",
  info: "text-status-info bg-status-infoBg",
};

export function RiskBadge({ risk }: { risk: string }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-medium tracking-wide ${RISK_STYLES[risk] || "text-ink-700 bg-surface-100"}`}>
      {risk}
    </span>
  );
}

export function PermissionBadge({ permission }: { permission: string }) {
  const label = permission === "APPROVAL_REQUIRED" ? "APPROVAL REQ." : permission;
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-medium ${PERMISSION_STYLES[permission] || "text-ink-700 bg-surface-100"}`}>
      {label}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded-sm text-xs font-medium ${STATE_STYLES[status] || "text-ink-700 bg-surface-100"}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-medium ${STATE_STYLES[severity] || RISK_STYLES[severity] || "text-ink-700 bg-surface-100"}`}>
      {severity}
    </span>
  );
}
