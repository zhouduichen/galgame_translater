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

  const color = character?.color ?? "#ffffff";

  function handleClick() {
    if (!complete) {
      skip();
    } else {
      onClick();
    }
  }

  return (
    <div
      className="absolute bottom-0 left-0 right-0 cursor-pointer bg-gradient-to-t from-[#0a0a0f]/95 via-[#0a0a0f]/90 to-transparent px-6 pb-6 pt-16"
      onClick={handleClick}
    >
      <div className="mx-auto max-w-3xl">
        {character && (
          <div className="mb-2 flex items-center gap-2">
            <span className="text-lg font-bold" style={{ color }}>{character.name}</span>
            {emotion && emotion !== "neutral" && (
              <span className="rounded bg-[#ffffff10] px-2 py-0.5 text-xs text-[#8888a0]">
                {emotion}
              </span>
            )}
          </div>
        )}
        <p className="min-h-[3em] text-lg leading-relaxed">
          {displayed}
          {!complete && <span className="ml-0.5 animate-pulse text-[#6688ff]">▌</span>}
        </p>
        {complete && (
          <p className="mt-2 text-xs text-[#555568] animate-pulse">
            {textSpeed <= 0 ? "Click to continue" : "▼ Click to continue"}
          </p>
        )}
      </div>
    </div>
  );
}
