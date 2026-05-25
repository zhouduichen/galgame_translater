"use client";

import type { ChoiceOption } from "@/lib/types";

type Props = {
  narration: string;
  options: ChoiceOption[];
  onChoose: (opt: ChoiceOption) => void;
};

export function ChoicePanel({ narration, options, onChoose }: Props) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black/60 px-6">
      <div className="mx-auto w-full max-w-xl">
        {narration && (
          <p className="mb-8 text-center text-lg text-[#cccce0]">{narration}</p>
        )}
        <div className="space-y-4">
          {options.map((opt, i) => (
            <button
              key={opt.option_id}
              className="w-full rounded-lg border border-[#2a2a3a] bg-[#1a1a25]/80 px-6 py-4 text-left text-[#e8e8f0] transition-all hover:border-[#6688ff] hover:bg-[#222233] hover:translate-x-1"
              onClick={() => onChoose(opt)}
            >
              <span className="mr-3 inline-flex h-6 w-6 items-center justify-center rounded-full border border-[#6688ff] text-xs text-[#6688ff]">
                {i + 1}
              </span>
              {opt.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
