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
    if (!complete) {
      skip();
    } else {
      onClick();
    }
  }

  return (
    <div
      className="absolute inset-0 flex cursor-pointer items-center justify-center px-8"
      onClick={handleClick}
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-lg italic leading-relaxed text-[#aaaac0]">{displayed}</p>
        {!complete && <span className="ml-0.5 animate-pulse text-[#6688ff]">▌</span>}
        {complete && (
          <p className="mt-4 text-xs text-[#555568] animate-pulse">Click to continue</p>
        )}
      </div>
    </div>
  );
}
