"use client";

import { ReactNode } from "react";
import { X } from "lucide-react";

export function Modal({ title, onClose, children, width = 420 }: { title: string; onClose: () => void; children: ReactNode; width?: number }) {
  return (
    <div className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-sm p-5 max-h-[90vh] overflow-y-auto w-full"
        style={{ maxWidth: width }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-ink-950">{title}</h3>
          <button onClick={onClose} className="text-ink-700/40 hover:text-ink-950">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const inputCls =
  "w-full border border-line rounded-sm px-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 bg-white";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-ink-700/70 mb-1">{label}</label>
      {children}
    </div>
  );
}

export function PrimaryButton({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="bg-ink-950 text-white text-xs font-medium rounded-sm px-3.5 py-1.5 hover:bg-ink-800 transition-colors disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, danger, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { danger?: boolean }) {
  return (
    <button
      {...props}
      className={`border border-line text-xs font-medium rounded-sm px-2.5 py-1 transition-colors disabled:opacity-40 ${
        danger ? "text-status-critical hover:border-status-critical" : "text-ink-700 hover:border-accent hover:text-accent"
      }`}
    >
      {children}
    </button>
  );
}
