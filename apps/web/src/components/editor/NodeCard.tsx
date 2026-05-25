"use client";

import { useState } from "react";
import type { StoryNode, Character, ChoiceOption } from "@/lib/types";
import type { Emotion, Side } from "@/lib/types";

type Props = {
  node: StoryNode;
  characters: Record<string, Character>;
  selected: boolean;
  nodeIds: string[];
  onSelect: () => void;
  onUpdate: (patch: Partial<StoryNode>) => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onAddOption?: () => void;
  onUpdateOption?: (optionId: string, patch: Partial<ChoiceOption>) => void;
  onDeleteOption?: (optionId: string) => void;
  isFirst: boolean;
  isLast: boolean;
};

const EMOTIONS: Emotion[] = ["neutral", "happy", "sad", "angry", "surprised", "shy", "thinking", "crying", "laughing"];
const SIDES: Side[] = ["left", "right", "center"];

const TYPE_COLORS: Record<string, string> = {
  dialogue: "border-l-[#6688ff]",
  narration: "border-l-[#88cc88]",
  choice: "border-l-[#ff8866]",
  scene_transition: "border-l-[#ffcc44]",
  ending: "border-l-[#ff6688]",
};

export function NodeCard({
  node,
  characters,
  selected,
  onSelect,
  onUpdate,
  onDelete,
  onMoveUp,
  onMoveDown,
  onAddOption,
  onUpdateOption,
  onDeleteOption,
  isFirst,
  isLast,
}: Props) {
  const [expanded, setExpanded] = useState(selected);

  function renderEditor() {
    switch (node.type) {
      case "dialogue":
        return (
          <div className="space-y-2">
            <select
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm text-[#e8e8f0]"
              value={node.character_id}
              onChange={(e) => onUpdate({ character_id: e.target.value })}
            >
              <option value="">-- character --</option>
              {Object.values(characters).map((c) => (
                <option key={c.character_id} value={c.character_id}>{c.name}</option>
              ))}
            </select>
            <div className="flex gap-2">
              <select
                className="rounded bg-[#0a0a0f] px-2 py-1.5 text-xs text-[#8888a0]"
                value={node.emotion}
                onChange={(e) => onUpdate({ emotion: e.target.value as Emotion })}
              >
                {EMOTIONS.map((e) => (
                  <option key={e} value={e}>{e}</option>
                ))}
              </select>
              <select
                className="rounded bg-[#0a0a0f] px-2 py-1.5 text-xs text-[#8888a0]"
                value={node.side}
                onChange={(e) => onUpdate({ side: e.target.value as Side })}
              >
                {SIDES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <textarea
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm text-[#e8e8f0]"
              rows={2}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="Dialogue text..."
            />
            <div className="flex items-center gap-2 text-xs text-[#555568]">
              <span>Next:</span>
              <code className="rounded bg-[#0a0a0f] px-1.5 py-0.5 text-[#6688ff]">
                {node.next_node_id || "(end)"}
              </code>
            </div>
          </div>
        );

      case "narration":
        return (
          <div className="space-y-2">
            <textarea
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm italic text-[#aaaac0]"
              rows={2}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="Narration text..."
            />
            <div className="flex items-center gap-2 text-xs text-[#555568]">
              <span>Next:</span>
              <code className="rounded bg-[#0a0a0f] px-1.5 py-0.5 text-[#6688ff]">
                {node.next_node_id || "(end)"}
              </code>
            </div>
          </div>
        );

      case "choice":
        return (
          <div className="space-y-3">
            <textarea
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm text-[#e8e8f0]"
              rows={1}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="Choice narration text (optional)..."
            />
            <div className="space-y-2">
              {node.options.map((opt) => (
                <div key={opt.option_id} className="flex items-start gap-2 rounded border border-[#2a2a3a] bg-[#0a0a0f] p-2">
                  <div className="flex-1 space-y-1">
                    <input
                      className="w-full bg-transparent text-sm text-[#e8e8f0]"
                      value={opt.text}
                      onChange={(e) => onUpdateOption?.(opt.option_id, { text: e.target.value })}
                      placeholder="Option text..."
                    />
                    <input
                      className="w-full bg-transparent text-xs text-[#6688ff]"
                      value={opt.next_node_id}
                      onChange={(e) => onUpdateOption?.(opt.option_id, { next_node_id: e.target.value })}
                      placeholder="Target node ID..."
                    />
                  </div>
                  <button
                    className="mt-1 text-xs text-red-400 hover:text-red-300"
                    onClick={() => onDeleteOption?.(opt.option_id)}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <button
              className="text-xs text-[#6688ff] hover:underline"
              onClick={onAddOption}
            >
              + Add option
            </button>
          </div>
        );

      case "scene_transition":
        return (
          <div className="space-y-2">
            <input
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm text-[#e8e8f0]"
              value={node.target_scene_id}
              onChange={(e) => onUpdate({ target_scene_id: e.target.value })}
              placeholder="Target scene ID..."
            />
          </div>
        );

      case "ending":
        return (
          <div className="space-y-2">
            <select
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm text-[#e8e8f0]"
              value={node.ending_type}
              onChange={(e) => onUpdate({ ending_type: e.target.value as any })}
            >
              <option value="neutral">Neutral</option>
              <option value="good">Good</option>
              <option value="bad">Bad</option>
              <option value="true">True</option>
            </select>
            <textarea
              className="w-full rounded bg-[#0a0a0f] px-2 py-1.5 text-sm italic text-[#aaaac0]"
              rows={2}
              value={node.epilogue}
              onChange={(e) => onUpdate({ epilogue: e.target.value })}
              placeholder="Epilogue text..."
            />
          </div>
        );

      default:
        return <p className="text-xs text-[#555568]">Unsupported node type: {node.type}</p>;
    }
  }

  return (
    <div
      className={`rounded-lg border border-[#2a2a3a] border-l-4 ${TYPE_COLORS[node.type] || "border-l-[#555]"} bg-[#13131a] transition-colors ${
        selected ? "ring-1 ring-[#6688ff]" : ""
      }`}
    >
      {/* Header */}
      <div
        className="flex cursor-pointer items-center justify-between px-3 py-2"
        onClick={() => { onSelect(); setExpanded(!expanded); }}
      >
        <div className="flex items-center gap-2">
          <span className="rounded bg-[#ffffff10] px-1.5 py-0.5 text-xs uppercase text-[#555568]">{node.type}</span>
          <code className="text-xs text-[#8888a0]">{node.node_id}</code>
        </div>
        <div className="flex items-center gap-1">
          <button
            className={`px-1.5 py-0.5 text-xs ${isFirst ? "text-[#333]" : "text-[#555568] hover:text-[#e8e8f0]"}`}
            disabled={isFirst}
            onClick={(e) => { e.stopPropagation(); onMoveUp(); }}
          >
            ▲
          </button>
          <button
            className={`px-1.5 py-0.5 text-xs ${isLast ? "text-[#333]" : "text-[#555568] hover:text-[#e8e8f0]"}`}
            disabled={isLast}
            onClick={(e) => { e.stopPropagation(); onMoveDown(); }}
          >
            ▼
          </button>
          <button
            className="px-1.5 py-0.5 text-xs text-red-400 hover:text-red-300"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            ×
          </button>
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div className="border-t border-[#2a2a3a] px-3 py-3">
          {renderEditor()}
        </div>
      )}
    </div>
  );
}
