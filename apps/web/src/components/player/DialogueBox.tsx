"use client";

import { useTypewriter } from "@/hooks/useTypewriter";
import type { Character, Emotion } from "@/lib/types";

type Props = {
  text: string;
  character?: Character | null;
  emotion?: Emotion;
  textSpeed: number;
  onComplete?: () => void;
  onClick: () => void;
};

export function DialogueBox({ text, character, emotion, textSpeed, onClick }: Props) {
  const { displayed, complete, skip } = useTypewriter(text, textSpeed);
  const color = character?.color ?? "#ff8ba0";

  function handleClick() {
    if (!complete) { skip(); }
    else { onClick(); }
  }

  return (
    <div
      className="absolute bottom-0 left-0 right-0 cursor-pointer px-6 pb-6 pt-16"
      style={{ background: "var(--player-gradient)" }}
      onClick={handleClick}
    >
      <div className="mx-auto max-w-3xl">
        {character && (
          <div className="mb-2 flex items-center gap-2">
            <span
              className="font-[family-name:var(--font-display)] text-lg font-semibold"
              style={{ color }}
            >
              {character.name}
            </span>
            {emotion && emotion !== "neutral" && (
              <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-[var(--text-secondary)]">
                {emotion}
              </span>
            )}
          </div>
        )}
        <p className="min-h-[3em] text-lg leading-relaxed text-[var(--text-primary)]">
          {displayed}
          {!complete && <span className="ml-0.5 animate-pulse text-sakura-pink">▌</span>}
        </p>
        {complete && (
          <p className="mt-2 animate-pulse text-xs text-[var(--text-muted)]">
            {textSpeed <= 0 ? "点击继续" : "▼ 点击继续"}
          </p>
        )}
      </div>
    </div>
  );
}
