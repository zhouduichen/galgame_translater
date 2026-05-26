"use client";

import { useState } from "react";
import Link from "next/link";

type Props = {
  id: string;
  title: string;
  onDelete?: (id: string) => void;
};

export function ProjectCard({ id, title, onDelete }: Props) {
  const [confirming, setConfirming] = useState(false);

  async function handleDelete() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    try {
      await fetch(`/api/projects/${id}`, { method: "DELETE" });
      onDelete?.(id);
    } catch {
      setConfirming(false);
    }
  }

  return (
    <div className="group rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] p-5 transition-all duration-300 hover:border-sakura-pink hover:shadow-[0_0_20px_var(--accent-glow)]">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h3>
        <div className="flex items-center gap-1.5">
          <span className="rounded-full bg-sakura-pink/10 px-2.5 py-0.5 text-[10px] font-medium tracking-wider text-sakura-pink">
            演示
          </span>
          {onDelete && (
            <button
              onClick={handleDelete}
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                confirming
                  ? "bg-[var(--error-red)]/20 text-[var(--error-red)]"
                  : "text-[var(--text-muted)] hover:bg-[var(--error-red)]/10 hover:text-[var(--error-red)]"
              }`}
            >
              {confirming ? "确认删除" : "✕"}
            </button>
          )}
        </div>
      </div>
      <p className="mb-4 text-xs text-[var(--text-muted)] font-mono">{id}</p>
      <div className="flex gap-2">
        <Link
          href={`/project/${id}`}
          className="rounded-lg bg-sakura-pink px-4 py-2 text-xs font-medium text-white transition-all duration-300 hover:bg-sakura-deep hover:shadow-[0_0_16px_var(--accent-glow)]"
        >
          播放
        </Link>
        <Link
          href={`/project/${id}/edit`}
          className="rounded-lg border border-[var(--bg-border)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-all duration-300 hover:border-sakura-pink hover:text-sakura-pink"
        >
          编辑
        </Link>
      </div>
    </div>
  );
}
