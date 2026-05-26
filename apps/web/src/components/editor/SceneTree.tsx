"use client";

import type { Scene } from "@/lib/types";

type Props = {
  scenes: Record<string, Scene>;
  currentSceneId: string | null;
  onSelect: (sceneId: string) => void;
};

export function SceneTree({ scenes, currentSceneId, onSelect }: Props) {
  return (
    <div className="space-y-1">
      {Object.values(scenes).map((scene) => (
        <button
          key={scene.scene_id}
          className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
            scene.scene_id === currentSceneId
              ? "bg-sakura-pink/20 text-sakura-pink"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]"
          }`}
          onClick={() => onSelect(scene.scene_id)}
        >
          <div className="font-medium">{scene.title}</div>
          <div className="mt-0.5 text-xs text-[var(--text-muted)]">{Object.keys(scene.nodes).length} 个节点</div>
        </button>
      ))}
    </div>
  );
}
