"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MetricCard, Panel, EmptyState } from "@/components/ui";
import { StatusPill } from "@/components/badges";
import { api } from "@/lib/api";
import type { EvaluationRun } from "@/lib/types";

const METRIC_LABELS: Record<string, string> = {
  intent_accuracy: "Intent Accuracy",
  tool_top1_accuracy: "Tool Top-1 Accuracy",
  tool_top3_recall: "Tool Top-3 Recall",
  risk_classification_accuracy: "Risk Classification Accuracy",
  permission_accuracy: "Permission Accuracy",
  unsafe_tool_call_rate: "Unsafe Tool Call Rate",
  approval_bypass_rate: "Approval Bypass Rate",
  prompt_injection_detection_rate: "Prompt Injection Detection Rate",
  prompt_injection_false_positive_rate: "Injection False-Positive Rate",
  tool_poisoning_detection_rate: "Tool Poisoning Detection Rate",
  evidence_sufficiency: "Evidence Sufficiency",
};

function isRateGood(key: string, value: number): boolean {
  const badWhenHigh = ["unsafe_tool_call_rate", "approval_bypass_rate", "prompt_injection_false_positive_rate"];
  if (badWhenHigh.includes(key)) return value < 0.1;
  return value > 0.7;
}

export default function EvaluationPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [sampleSize, setSampleSize] = useState(100);

  async function load() {
    setLoading(true);
    const data = (await api.listEvaluationResults()) as EvaluationRun[];
    setRuns(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function triggerRun() {
    setRunning(true);
    try {
      await api.runEvaluation("enterprise_tool_routing_v1", sampleSize);
      await load();
    } finally {
      setRunning(false);
    }
  }

  const latest = runs[0];

  return (
    <AppShell title="Evaluation Dashboard">
      <div className="flex items-center gap-2 mb-4">
        <input
          type="number"
          value={sampleSize}
          onChange={(e) => setSampleSize(Number(e.target.value))}
          className="border border-line rounded-sm px-2 py-1.5 text-xs w-24"
          min={10}
          max={2000}
        />
        <span className="text-xs text-ink-700/50">sample size</span>
        <button
          onClick={triggerRun}
          disabled={running}
          className="ml-auto bg-ink-950 text-white text-xs font-medium rounded-sm px-4 py-1.5 hover:bg-ink-800 disabled:opacity-50"
        >
          {running ? "Running evaluation…" : "Run New Evaluation"}
        </button>
      </div>

      {loading ? (
        <EmptyState message="Loading…" />
      ) : !latest ? (
        <Panel title="Evaluation Results">
          <EmptyState message="No evaluation run available. Trigger one above." />
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-3 mb-3">
            {Object.entries(latest.metrics)
              .filter(([k]) => !k.includes("latency"))
              .map(([key, value]) => (
                <MetricCard
                  key={key}
                  label={METRIC_LABELS[key] || key}
                  value={`${(value * 100).toFixed(1)}%`}
                  tone={isRateGood(key, value) ? "healthy" : "warning"}
                />
              ))}
          </div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <MetricCard
              label="Avg Tool Latency"
              value={`${(latest.metrics.avg_tool_latency_ms ?? 0).toFixed(1)} ms`}
              sublabel="per tool execution"
            />
            <MetricCard
              label="Avg End-to-End Latency"
              value={`${(latest.metrics.avg_e2e_latency_ms ?? 0).toFixed(1)} ms`}
              sublabel="intent -> retrieval -> scoring"
            />
          </div>
        </>
      )}

      <Panel title="Evaluation Runs">
        {runs.length === 0 ? (
          <EmptyState message="No runs yet." />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-left text-ink-700/50 border-b border-line">
                <th className="font-medium pb-1.5">Dataset</th>
                <th className="font-medium pb-1.5">Model Version</th>
                <th className="font-medium pb-1.5">Status</th>
                <th className="font-medium pb-1.5">Started</th>
                <th className="font-medium pb-1.5 text-right">Intent Acc.</th>
                <th className="font-medium pb-1.5 text-right">Tool Top-1</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-line last:border-0">
                  <td className="py-1.5">{run.dataset_name}</td>
                  <td className="py-1.5 font-mono text-ink-700/60">{run.model_version}</td>
                  <td className="py-1.5"><StatusPill status={run.status === "COMPLETED" ? "healthy" : "warning"} /></td>
                  <td className="py-1.5 text-ink-700/50">{new Date(run.started_at).toLocaleString()}</td>
                  <td className="py-1.5 text-right tabular">{((run.metrics.intent_accuracy ?? 0) * 100).toFixed(1)}%</td>
                  <td className="py-1.5 text-right tabular">{((run.metrics.tool_top1_accuracy ?? 0) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Panel>
    </AppShell>
  );
}
