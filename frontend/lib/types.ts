export interface User {
  id: string;
  email: string;
  full_name: string;
  role_name: string;
  department?: string | null;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  requires_approval: boolean;
  required_roles: string[];
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  enabled: boolean;
  version: string;
  success_rate: number;
  avg_latency_ms: number;
  execution_count: number;
  last_used: string | null;
}

export interface EvidenceItem {
  tool_name: string;
  execution_id: string;
  timestamp: string;
  target: string;
  status: string;
  latency_ms: number;
  result: Record<string, unknown>;
  source: string;
}

export interface RoutingCandidate {
  name: string;
  similarity: number;
  risk: string;
  permission: string;
  final_score: number;
}

export interface Plan {
  intent: string;
  objective: string;
  required_information: string[];
  candidate_tools: string[];
  reasoning_summary: string;
  risk_level: string;
  requires_approval: boolean;
}

export interface Verification {
  verified: boolean;
  confidence: number;
  issues: string[];
  required_action: string;
}

export interface AgentQueryResponse {
  request_id: string;
  intent: string;
  risk_level: string;
  permission_result: string;
  routing_candidates: RoutingCandidate[];
  selected_tools: string[];
  executions: EvidenceItem[];
  evidence: EvidenceItem[];
  plan: Plan;
  answer: string;
  verification: Verification;
  audit_id: string;
  pending_approval_id: string | null;
  security_findings: string[];
  total_latency_ms: number;
}

export interface Approval {
  id: string;
  request_id: string;
  tool_name: string;
  requested_by_role: string;
  target: string;
  reason: string;
  risk_level: string;
  required_role: string;
  status: string;
  requested_at: string;
  decided_at: string | null;
}

export interface AuditLog {
  id: string;
  request_id: string;
  user_id: string;
  user_role: string;
  user_query: string;
  detected_intent: string;
  candidate_tools: string[];
  selected_tools: string[];
  risk_level: string;
  permission_result: string;
  approval_status: string;
  execution_latency_ms: number;
  final_response: string;
  status: string;
  created_at: string;
}

export interface Incident {
  id: string;
  code: string;
  title: string;
  severity: string;
  service: string;
  status: string;
  root_cause: string;
  detected_at: string;
  assigned_to: string | null;
}

export interface SecurityEvent {
  id: string;
  request_id: string;
  event_type: string;
  severity: string;
  description: string;
  blocked: boolean;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  dataset_name: string;
  model_version: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  metrics: Record<string, number>;
}

export interface RagSearchResult {
  document_id: string;
  title: string;
  category: string;
  similarity: number;
  snippet: string;
}

export interface SystemHealth {
  api: string;
  mcp_gateway: string;
  database: string;
  vector_store: string;
  llm_service: string;
  redis: string;
  environment: string;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role_name: string;
  department: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  role_name: string;
  is_active: boolean;
  last_used: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  role_name: string;
  raw_key: string;
  key_prefix: string;
  created_at: string;
}

export interface RoleItem {
  id: string;
  name: string;
  description: string;
  max_risk_level: string;
  is_elevated: boolean;
}

export interface PermissionItem {
  id: string;
  role_name: string;
  category: string;
  allowed: boolean;
}

export interface ToolExecution {
  id: string;
  execution_id: string;
  request_id: string;
  tool_name: string;
  target: string;
  status: string;
  latency_ms: number;
  result: Record<string, unknown>;
  source: string;
  timestamp: string;
}

export interface ToolPayload {
  name?: string;
  description?: string;
  category?: string;
  risk_level?: string;
  requires_approval?: boolean;
  required_roles?: string[];
  timeout_seconds?: number;
  enabled?: boolean;
  version?: string;
}

export const ALL_ROLES = [
  "Viewer",
  "IT Support",
  "Network Engineer",
  "Database Administrator",
  "System Administrator",
  "Security Analyst",
  "Infrastructure Administrator",
  "Enterprise Administrator",
];
export const ALL_CATEGORIES = ["network", "server", "database", "security", "logging", "knowledge"];
export const ADMIN_ROLES = ["Infrastructure Administrator", "Enterprise Administrator"];
