"use client";

import { useTypewriter } from "@/hooks/useTypewriter";

type Props = {
  text: string;
  textSpeed: number;
  onClick: () => void;
};

export function NarrationBox({ text, textSpeed, onClick }: Props) {
  const { displayed, complete, skip } = useTypewriter(text, textSpeed);

  function handleClick() {
    if (!complete) { skip(); }
    else { onClick(); }
  }

  return (
    <div
      className="absolute inset-0 flex cursor-pointer items-center justify-center px-8"
      onClick={handleClick}
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-lg italic leading-relaxed text-[var(--text-primary)]/80">{displayed}</p>
        {!complete && <span className="ml-0.5 animate-pulse text-sakura-pink">▌</span>}
        {complete && (
          <p className="mt-4 animate-pulse text-xs text-[var(--text-muted)]">点击继续</p>
        )}
      </div>
    </div>
  );
}
