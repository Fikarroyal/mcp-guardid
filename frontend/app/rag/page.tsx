"use client";

import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Panel, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import type { RagSearchResult } from "@/lib/types";

export default function RagKnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RagSearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    const data = (await api.ragSearch(query.trim())) as RagSearchResult[];
    setResults(data);
    setLoading(false);
  }

  return (
    <AppShell title="RAG Knowledge Base">
      <Panel title="Search SOPs, Incident History &amp; Documentation">
        <form onSubmit={onSubmit} className="flex gap-2 mb-1">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-700/40" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. database timeout"
              className="w-full border border-line rounded-sm pl-8 pr-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent/30"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-ink-950 text-white text-sm font-medium rounded-sm px-4 hover:bg-ink-800 disabled:opacity-50"
          >
            Search
          </button>
        </form>
      </Panel>

      <div className="mt-4">
        <Panel title="Results">
          {!results ? (
            <EmptyState message="Search the knowledge base to see relevant SOPs, incidents, and documentation." />
          ) : results.length === 0 ? (
            <EmptyState message="No relevant documents found." />
          ) : (
            <ul className="space-y-2.5">
              {results.map((r) => (
                <li key={r.document_id} className="border border-line rounded-sm px-3 py-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-ink-950">{r.title}</span>
                    <span className="text-[10.5px] tabular text-ink-700/50">{(r.similarity * 100).toFixed(0)}% match</span>
                  </div>
                  <div className="text-[10.5px] text-accent font-medium mb-1.5">{r.category}</div>
                  <p className="text-xs text-ink-700/70 leading-relaxed">{r.snippet}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}
