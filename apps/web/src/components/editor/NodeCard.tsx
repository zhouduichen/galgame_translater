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
  dialogue: "border-l-sakura-pink",
  narration: "border-l-[#6bcb9e]",
  choice: "border-l-[#ff8866]",
  scene_transition: "border-l-[#ffcc44]",
  ending: "border-l-[#ff6688]",
};

const TYPE_LABELS: Record<string, string> = {
  dialogue: "对白",
  narration: "旁白",
  choice: "选项",
  scene_transition: "转场",
  branch: "分支",
  ending: "结局",
};

const EMOTION_LABELS: Record<Emotion, string> = {
  neutral: "平静",
  happy: "开心",
  sad: "难过",
  angry: "生气",
  surprised: "惊讶",
  shy: "害羞",
  thinking: "思考",
  crying: "哭泣",
  laughing: "大笑",
};

const SIDE_LABELS: Record<Side, string> = {
  left: "左侧",
  right: "右侧",
  center: "中间",
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
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
              value={node.character_id}
              onChange={(e) => onUpdate({ character_id: e.target.value })}
            >
              <option value="">-- 角色 --</option>
              {Object.values(characters).map((c) => (
                <option key={c.character_id} value={c.character_id}>{c.name}</option>
              ))}
            </select>
            <div className="flex gap-2">
              <select
                className="rounded bg-[var(--bg-deep)] px-2 py-1.5 text-xs text-[var(--text-secondary)]"
                value={node.emotion}
                onChange={(e) => onUpdate({ emotion: e.target.value as Emotion })}
              >
                {EMOTIONS.map((e) => (
                  <option key={e} value={e}>{EMOTION_LABELS[e]}</option>
                ))}
              </select>
              <select
                className="rounded bg-[var(--bg-deep)] px-2 py-1.5 text-xs text-[var(--text-secondary)]"
                value={node.side}
                onChange={(e) => onUpdate({ side: e.target.value as Side })}
              >
                {SIDES.map((s) => (
                  <option key={s} value={s}>{SIDE_LABELS[s]}</option>
                ))}
              </select>
            </div>
            <textarea
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
              rows={2}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="对白文本..."
            />
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
              <span>下一节点：</span>
              <code className="rounded bg-[var(--bg-deep)] px-1.5 py-0.5 text-sakura-pink">
                {node.next_node_id || "（结束）"}
              </code>
            </div>
          </div>
        );

      case "narration":
        return (
          <div className="space-y-2">
            <textarea
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm italic text-[var(--text-primary)]/80"
              rows={2}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="旁白文本..."
            />
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
              <span>下一节点：</span>
              <code className="rounded bg-[var(--bg-deep)] px-1.5 py-0.5 text-sakura-pink">
                {node.next_node_id || "（结束）"}
              </code>
            </div>
          </div>
        );

      case "choice":
        return (
          <div className="space-y-3">
            <textarea
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
              rows={1}
              value={node.text}
              onChange={(e) => onUpdate({ text: e.target.value })}
              placeholder="选择前的旁白（可选）..."
            />
            <div className="space-y-2">
              {node.options.map((opt) => (
                <div key={opt.option_id} className="flex items-start gap-2 rounded border border-[var(--bg-border)] bg-[var(--bg-deep)] p-2">
                  <div className="flex-1 space-y-1">
                    <input
                      className="w-full bg-transparent text-sm text-[var(--text-primary)]"
                      value={opt.text}
                      onChange={(e) => onUpdateOption?.(opt.option_id, { text: e.target.value })}
                      placeholder="选项文本..."
                    />
                    <input
                      className="w-full bg-transparent text-xs text-sakura-pink"
                      value={opt.next_node_id}
                      onChange={(e) => onUpdateOption?.(opt.option_id, { next_node_id: e.target.value })}
                      placeholder="目标节点 ID..."
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
              className="text-xs text-sakura-pink hover:underline"
              onClick={onAddOption}
            >
              + 添加选项
            </button>
          </div>
        );

      case "scene_transition":
        return (
          <div className="space-y-2">
            <input
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
              value={node.target_scene_id}
              onChange={(e) => onUpdate({ target_scene_id: e.target.value })}
              placeholder="目标场景 ID..."
            />
          </div>
        );

      case "ending":
        return (
          <div className="space-y-2">
            <select
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
              value={node.ending_type}
              onChange={(e) => onUpdate({ ending_type: e.target.value as any })}
            >
              <option value="neutral">普通</option>
              <option value="good">好结局</option>
              <option value="bad">坏结局</option>
              <option value="true">真结局</option>
            </select>
            <textarea
              className="w-full rounded bg-[var(--bg-deep)] px-2 py-1.5 text-sm italic text-[var(--text-primary)]/80"
              rows={2}
              value={node.epilogue}
              onChange={(e) => onUpdate({ epilogue: e.target.value })}
              placeholder="结尾文本..."
            />
          </div>
        );

      default:
        return <p className="text-xs text-[var(--text-muted)]">暂不支持的节点类型：{node.type}</p>;
    }
  }

  return (
    <div
      className={`rounded-lg border border-[var(--bg-border)] border-l-4 ${TYPE_COLORS[node.type] || "border-l-[#555]"} bg-[var(--bg-panel)] transition-colors ${
        selected ? "ring-1 ring-sakura-pink" : ""
      }`}
    >
      {/* Header */}
      <div
        className="flex cursor-pointer items-center justify-between px-3 py-2"
        onClick={() => { onSelect(); setExpanded(!expanded); }}
      >
        <div className="flex items-center gap-2">
          <span className="rounded bg-[#ffffff10] px-1.5 py-0.5 text-xs text-[var(--text-muted)]">
            {TYPE_LABELS[node.type] ?? node.type}
          </span>
          <code className="text-xs text-[var(--text-secondary)]">{node.node_id}</code>
        </div>
        <div className="flex items-center gap-1">
          <button
            className={`px-1.5 py-0.5 text-xs ${isFirst ? "text-[#333]" : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"}`}
            disabled={isFirst}
            onClick={(e) => { e.stopPropagation(); onMoveUp(); }}
          >
            ↑
          </button>
          <button
            className={`px-1.5 py-0.5 text-xs ${isLast ? "text-[#333]" : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"}`}
            disabled={isLast}
            onClick={(e) => { e.stopPropagation(); onMoveDown(); }}
          >
            ↓
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
        <div className="border-t border-[var(--bg-border)] px-3 py-3">
          {renderEditor()}
        </div>
      )}
    </div>
  );
}
