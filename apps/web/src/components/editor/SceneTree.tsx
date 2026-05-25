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
              ? "bg-[#6688ff]/20 text-[#6688ff]"
              : "text-[#8888a0] hover:bg-[#1a1a25] hover:text-[#e8e8f0]"
          }`}
          onClick={() => onSelect(scene.scene_id)}
        >
          <div className="font-medium">{scene.title}</div>
          <div className="mt-0.5 text-xs text-[#555568]">{Object.keys(scene.nodes).length} nodes</div>
        </button>
      ))}
    </div>
  );
}
