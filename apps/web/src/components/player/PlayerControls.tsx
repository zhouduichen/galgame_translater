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
  status,
  autoMode,
  textSpeed,
  hasHistory,
  onBack,
  onToggleAuto,
  onTextSpeedChange,
  onRestart,
}: Props) {
  return (
    <div className="absolute right-4 top-4 flex items-center gap-2">
      {/* Back */}
      {hasHistory && (
        <button
          className="rounded bg-[#1a1a25]/80 px-3 py-1.5 text-xs text-[#8888a0] transition-colors hover:text-[#e8e8f0]"
          onClick={onBack}
        >
          Back
        </button>
      )}

      {/* Auto */}
      <button
        className={`rounded px-3 py-1.5 text-xs transition-colors ${
          autoMode
            ? "bg-[#6688ff]/30 text-[#6688ff]"
            : "bg-[#1a1a25]/80 text-[#8888a0] hover:text-[#e8e8f0]"
        }`}
        onClick={onToggleAuto}
      >
        {autoMode ? "AUTO ON" : "AUTO"}
      </button>

      {/* Speed */}
      <select
        className="rounded bg-[#1a1a25]/80 px-2 py-1.5 text-xs text-[#8888a0]"
        value={textSpeed}
        onChange={(e) => onTextSpeedChange(Number(e.target.value))}
      >
        <option value={0}>Instant</option>
        <option value={20}>Fast</option>
        <option value={40}>Normal</option>
        <option value={80}>Slow</option>
      </select>

      {/* Restart */}
      {status === "ended" && (
        <button
          className="rounded bg-[#1a1a25]/80 px-3 py-1.5 text-xs text-[#8888a0] transition-colors hover:text-[#e8e8f0]"
          onClick={onRestart}
        >
          Restart
        </button>
      )}
    </div>
  );
}
