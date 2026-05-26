"use client";

import type { PlayerStatus } from "@/stores/playerStore";

type Props = {
  status: PlayerStatus;
  autoMode: boolean;
  textSpeed: number;
  hasHistory: boolean;
  onBack: () => void;
  onToggleAuto: () => void;
  onTextSpeedChange: (speed: number) => void;
  onRestart: () => void;
};

export function PlayerControls({
  status, autoMode, textSpeed, hasHistory,
  onBack, onToggleAuto, onTextSpeedChange, onRestart,
}: Props) {
  return (
    <div className="absolute right-4 top-4 flex items-center gap-2">
      {hasHistory && (
        <button
          className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-3 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink hover:text-[var(--text-primary)]"
          onClick={onBack}
        >
          返回
        </button>
      )}

      <button
        className={`rounded-lg border px-3 py-1.5 text-xs font-medium backdrop-blur-sm transition-all duration-200 ${
          autoMode
            ? "border-sakura-pink bg-sakura-pink/15 text-sakura-pink"
            : "border-[var(--bg-border)] bg-[var(--bg-card)]/80 text-[var(--text-secondary)] hover:border-sakura-pink hover:text-[var(--text-primary)]"
        }`}
        onClick={onToggleAuto}
      >
        自动
      </button>

      <select
        className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-2 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink"
        value={textSpeed}
        onChange={(e) => onTextSpeedChange(Number(e.target.value))}
      >
        <option value={0}>即时</option>
        <option value={20}>快速</option>
        <option value={40}>普通</option>
        <option value={80}>慢速</option>
      </select>

      {status === "ended" && (
        <button
          className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 px-3 py-1.5 text-xs text-[var(--text-secondary)] backdrop-blur-sm transition-all duration-200 hover:border-sakura-pink hover:text-[var(--text-primary)]"
          onClick={onRestart}
        >
          重来
        </button>
      )}
    </div>
  );
}
