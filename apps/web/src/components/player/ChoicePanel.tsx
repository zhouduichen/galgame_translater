"use client";

import type { ChoiceOption } from "@/lib/types";

type Props = {
  narration: string;
  options: ChoiceOption[];
  onChoose: (opt: ChoiceOption) => void;
};

export function ChoicePanel({ narration, options, onChoose }: Props) {
  return (
    <div className="absolute inset-0 flex items-center justify-center px-6" style={{ background: "var(--bg-overlay)" }}>
      <div className="mx-auto w-full max-w-xl">
        {narration && (
          <p className="mb-8 text-center text-lg text-[var(--text-primary)]/80">{narration}</p>
        )}
        <div className="space-y-3">
          {options.map((opt, i) => (
            <button
              key={opt.option_id}
              className="group w-full rounded-xl border border-[var(--bg-border)] bg-[var(--bg-card)] px-6 py-4 text-left text-[var(--text-primary)] transition-all duration-300 hover:border-sakura-pink hover:bg-sakura-pink/5 hover:translate-x-1"
              onClick={() => onChoose(opt)}
            >
              <span className="mr-3 inline-flex h-6 w-6 items-center justify-center rounded-full border border-sakura-pink text-xs text-sakura-pink transition-all duration-300 group-hover:bg-sakura-pink group-hover:text-white">
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
