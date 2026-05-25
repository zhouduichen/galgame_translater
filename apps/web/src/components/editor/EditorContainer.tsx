"use client";

import { useEffect, useMemo } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { SceneTree } from "./SceneTree";
import { NodeCard } from "./NodeCard";
import type { Project, StoryNode } from "@/lib/types";
import { getNodeIdsInOrder } from "@/lib/types";

type Props = {
  project: Project;
  onBackToPlayer: () => void;
};

export function EditorContainer({ project, onBackToPlayer }: Props) {
  const store = useEditorStore();

  useEffect(() => {
    store.loadProject(project);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.project_id]);

  const {
    currentSceneId,
    selectedNodeId,
    dirty,
    selectScene,
    selectNode,
    updateNode,
    addNode,
    deleteNode,
    reorderNode,
    updateChoiceOption,
    addChoiceOption,
    deleteChoiceOption,
    saveProject,
  } = store;

  const currentScene = currentSceneId ? store.project?.scenes[currentSceneId] ?? null : null;

  const orderedNodeIds = useMemo(() => {
    if (!currentScene) return [];
    const ids = getNodeIdsInOrder(currentScene);
    // Add any nodes that aren't in the linear chain (e.g., choice targets, scene transitions)
    const allIds = Object.keys(currentScene.nodes);
    const extra = allIds.filter((id) => !ids.includes(id));
    return [...ids, ...extra];
  }, [currentScene]);

  if (!currentScene) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[#8888a0]">No scene selected</p>
      </div>
    );
  }

  const characters = store.project?.characters ?? {};

  return (
    <div className="flex h-screen bg-[#0a0a0f]">
      {/* Left: Scene tree */}
      <div className="w-56 flex-shrink-0 border-r border-[#2a2a3a] overflow-y-auto p-3">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#8888a0]">Scenes</h2>
          <span className="text-xs text-[#555568]">{Object.keys(store.project?.scenes ?? {}).length}</span>
        </div>
        <SceneTree
          scenes={store.project?.scenes ?? {}}
          currentSceneId={currentSceneId}
          onSelect={selectScene}
        />
      </div>

      {/* Center: Node timeline */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#e8e8f0]">{currentScene.title}</h2>
            <p className="text-xs text-[#555568]">{currentScene.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="rounded bg-[#1a1a25] px-3 py-1.5 text-xs text-[#8888a0] transition-colors hover:text-[#e8e8f0]"
              onClick={onBackToPlayer}
            >
              Play
            </button>
            <button
              className={`rounded px-3 py-1.5 text-xs transition-colors ${
                dirty
                  ? "bg-[#6688ff] text-white hover:bg-[#5577ee]"
                  : "bg-[#1a1a25] text-[#555568]"
              }`}
              onClick={saveProject}
              disabled={!dirty}
            >
              {dirty ? "Save" : "Saved"}
            </button>
          </div>
        </div>

        {/* Add node buttons */}
        <div className="mb-4 flex gap-2">
          {(["dialogue", "narration", "choice"] as const).map((type) => (
            <button
              key={type}
              className="rounded border border-[#2a2a3a] bg-[#1a1a25] px-3 py-1.5 text-xs text-[#8888a0] transition-colors hover:border-[#6688ff] hover:text-[#e8e8f0]"
              onClick={() => {
                const lastNodeId = orderedNodeIds[orderedNodeIds.length - 1];
                addNode(type, lastNodeId);
              }}
            >
              + {type}
            </button>
          ))}
        </div>

        {/* Node list */}
        <div className="space-y-2">
          {orderedNodeIds.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#555568]">No nodes in this scene. Add one above.</p>
          ) : (
            orderedNodeIds.map((nodeId, idx) => {
              const node = currentScene.nodes[nodeId];
              if (!node) return null;
              return (
                <NodeCard
                  key={nodeId}
                  node={node as StoryNode}
                  characters={characters}
                  selected={selectedNodeId === nodeId}
                  nodeIds={orderedNodeIds}
                  onSelect={() => selectNode(nodeId)}
                  onUpdate={(patch) => updateNode(nodeId, patch)}
                  onDelete={() => deleteNode(nodeId)}
                  onMoveUp={() => reorderNode(nodeId, "up")}
                  onMoveDown={() => reorderNode(nodeId, "down")}
                  isFirst={idx === 0}
                  isLast={idx === orderedNodeIds.length - 1}
                  onAddOption={
                    node.type === "choice"
                      ? () => addChoiceOption(nodeId)
                      : undefined
                  }
                  onUpdateOption={
                    node.type === "choice"
                      ? (optId, patch) => updateChoiceOption(nodeId, optId, patch)
                      : undefined
                  }
                  onDeleteOption={
                    node.type === "choice"
                      ? (optId) => deleteChoiceOption(nodeId, optId)
                      : undefined
                  }
                />
              );
            })
          )}
        </div>
      </div>

      {/* Right: Inspector / info */}
      <div className="w-64 flex-shrink-0 border-l border-[#2a2a3a] overflow-y-auto p-3">
        <h3 className="mb-3 text-sm font-semibold text-[#8888a0]">Inspector</h3>
        {selectedNodeId && currentScene.nodes[selectedNodeId] ? (
          <div className="space-y-3 text-xs text-[#8888a0]">
            <div>
              <span className="text-[#555568]">ID:</span>{" "}
              <code className="text-[#6688ff]">{selectedNodeId}</code>
            </div>
            <div>
              <span className="text-[#555568]">Type:</span>{" "}
              <span className="capitalize">{currentScene.nodes[selectedNodeId].type}</span>
            </div>
            {orderedNodeIds.indexOf(selectedNodeId) >= 0 && (
              <div>
                <span className="text-[#555568]">Position:</span>{" "}
                {orderedNodeIds.indexOf(selectedNodeId) + 1} / {orderedNodeIds.length}
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-[#555568]">Select a node to inspect</p>
        )}

        <div className="mt-6">
          <h4 className="mb-2 text-xs font-semibold text-[#555568]">Node Types</h4>
          <div className="space-y-1 text-xs text-[#555568]">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#6688ff]" />
              dialogue
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#88cc88]" />
              narration
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ff8866]" />
              choice
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ffcc44]" />
              transition
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded bg-[#ff6688]" />
              ending
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
